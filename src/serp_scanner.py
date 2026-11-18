import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.matriz_negocio import (
    MEDIDAS_PNEUS_CHAVE,
    SERP_PROVIDERS,
    UNIDADES,
    SERVICOS,
    slugify,
    normalize_url,
)

logger = logging.getLogger(__name__)

QUOTA_FILE = Path(".cache/serp_quota.json")
CACHE_FILE = Path(".cache/cache_serp.json")
CACHE_TTL_DAYS = 7


def _load_quota() -> dict:
    current_month = datetime.now().strftime("%Y-%m")
    default = {
        "reset_month": current_month,
        **{p["name"]: {"used": 0} for p in SERP_PROVIDERS},
        "cooldowns": {p["name"]: None for p in SERP_PROVIDERS},
    }
    if QUOTA_FILE.exists():
        try:
            data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            if data.get("reset_month") != current_month:
                for p in SERP_PROVIDERS:
                    data[p["name"]] = {"used": 0}
                data["reset_month"] = current_month
            # Garantir que cooldowns existe
            if "cooldowns" not in data:
                data["cooldowns"] = {p["name"]: None for p in SERP_PROVIDERS}
            return data
        except Exception:
            pass
    return default


def _save_quota(quota: dict):
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(quota, indent=2, default=str), encoding="utf-8")


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


_ALERT_THRESHOLD = 0.80   # avisar ao atingir 80% da cota
_SWITCH_THRESHOLD = 0.90  # trocar para o próximo provedor ao atingir 90%


def _check_quota_alerts(quota: dict):
    """Loga aviso quando um provedor atinge 80% da cota mensal."""
    for p in SERP_PROVIDERS:
        limit = p["monthly_quota"]
        if limit >= 999_999:
            continue
        used = quota.get(p["name"], {}).get("used", 0)
        pct = used / limit
        if pct >= 1.0:
            logger.warning(
                f"[COTA ESGOTADA] {p['name'].upper()}: {used}/{limit} queries usadas. "
                f"Trocando automaticamente para o próximo provedor."
            )
        elif pct >= _ALERT_THRESHOLD:
            remaining = limit - used
            logger.warning(
                f"[COTA {int(pct*100)}%] {p['name'].upper()}: {used}/{limit} queries usadas "
                f"({remaining} restantes). Próximo provedor será acionado em breve."
            )


def _select_provider(quota: dict) -> dict | None:
    _check_quota_alerts(quota)
    for p in sorted(SERP_PROVIDERS, key=lambda x: x["priority"]):
        key = os.environ.get(p["env_key"])
        if not key:
            continue
        used = quota.get(p["name"], {}).get("used", 0)
        limit = p["monthly_quota"]
        if used >= limit:
            logger.info(f"[SKIP] {p['name']}: cota mensal esgotada ({used}/{limit}).")
            continue
        cooldown = quota.get("cooldowns", {}).get(p["name"])
        if cooldown and datetime.fromisoformat(cooldown) > datetime.now():
            logger.info(f"[SKIP] {p['name']}: em cooldown até {cooldown}.")
            continue
        # BLOQUEIO ABSOLUTO: DataForSEO é pago — nunca usar sem flag explícita
        if p["name"] == "dataforseo":
            allow_paid = os.environ.get("ALLOW_PAID_SERP", "false").lower() == "true"
            if not allow_paid:
                logger.warning(
                    "[BLOQUEADO] DataForSEO é um provedor PAGO e está desativado por segurança. "
                    "Para habilitar, defina ALLOW_PAID_SERP=true no .env (não recomendado)."
                )
                continue

        pct = used / limit if limit < 999_999 else 0

        # 90% → trocar para o próximo provedor automaticamente
        if pct >= _SWITCH_THRESHOLD:
            remaining = limit - used
            logger.warning(
                f"[TROCA AUTOMÁTICA] {p['name'].upper()} atingiu {int(pct*100)}% da cota "
                f"({remaining} queries restantes). Trocando para: {_next_provider_name(p['priority'])}."
            )
            continue  # pula este provedor, tenta o próximo

        # 80% → avisa mas ainda usa
        if pct >= _ALERT_THRESHOLD:
            remaining = limit - used
            logger.warning(
                f"[AVISO 80%] {p['name'].upper()}: {used}/{limit} queries usadas. "
                f"Troca automática ocorrerá ao atingir 90%."
            )

        return p
    logger.warning(
        "Todas as cotas gratuitas esgotadas este mês. "
        "Nenhuma query será enviada (DataForSEO bloqueado por padrão). "
        "Os dados do cache da semana anterior serão usados onde disponíveis."
    )
    return None


def _next_provider_name(current_priority: int) -> str:
    candidates = sorted(SERP_PROVIDERS, key=lambda x: x["priority"])
    for p in candidates:
        if p["priority"] > current_priority and os.environ.get(p["env_key"]):
            return p["name"].upper()
    return "NENHUM (DataForSEO será acionado como overflow)"


def _set_cooldown(quota: dict, provider_name: str):
    expiry = (datetime.now() + timedelta(hours=1)).isoformat()
    if "cooldowns" not in quota:
        quota["cooldowns"] = {}
    quota["cooldowns"][provider_name] = expiry
    logger.warning(f"Provider '{provider_name}' em cooldown por 1h.")


@retry(wait=wait_exponential(multiplier=1, min=2, max=32),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(requests.RequestException))
def _search_brave(query: str, key: str) -> list[dict]:
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": 10, "country": "BR", "search_lang": "pt"},
        timeout=30,
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["title"]}
            for r in resp.json().get("web", {}).get("results", [])]


@retry(wait=wait_exponential(multiplier=1, min=2, max=32),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(requests.RequestException))
def _search_bing(query: str, key: str) -> list[dict]:
    resp = requests.get(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": key},
        params={"q": query, "count": 10, "mkt": "pt-BR", "cc": "BR"},
        timeout=30,
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["name"]}
            for r in resp.json().get("webPages", {}).get("value", [])]


@retry(wait=wait_exponential(multiplier=1, min=2, max=32),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(requests.RequestException))
def _search_tavily(query: str, key: str) -> list[dict]:
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": 10,
              "include_domains": [], "search_depth": "basic"},
        timeout=30,
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["title"]}
            for r in resp.json().get("results", [])]


@retry(wait=wait_exponential(multiplier=1, min=2, max=32),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(requests.RequestException))
def _search_dataforseo(query: str, login_b64: str) -> list[dict]:
    import base64
    creds = base64.b64decode(login_b64).decode()
    login, password = creds.split(":", 1)
    resp = requests.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        auth=(login, password),
        json=[{"keyword": query, "location_name": "Brazil",
               "language_name": "Portuguese", "depth": 10}],
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json()["tasks"][0]["result"][0].get("items", [])
    return [{"url": i["url"], "title": i["title"]}
            for i in items if i.get("type") == "organic"]


def _do_search(query: str, quota: dict, cache: dict) -> list[dict] | None:
    cache_key = slugify(query)
    cached = cache.get(cache_key)
    if cached:
        cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
        if (datetime.now() - cached_at).days < CACHE_TTL_DAYS:
            return cached.get("results", [])

    provider = _select_provider(quota)
    if not provider:
        logger.error(f"Nenhum provedor disponível para: {query}")
        return None

    key = os.environ.get(provider["env_key"])
    results = None
    try:
        name = provider["name"]
        if name == "brave":
            results = _search_brave(query, key)
        elif name == "bing":
            results = _search_bing(query, key)
        elif name == "tavily":
            results = _search_tavily(query, key)
        elif name == "dataforseo":
            results = _search_dataforseo(query, key)

        quota[name]["used"] = quota[name].get("used", 0) + 1
        cache[cache_key] = {"results": results, "cached_at": datetime.now().isoformat()}
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (429, 503):
            _set_cooldown(quota, provider["name"])
        logger.error(f"Erro HTTP ao buscar '{query}': {e}")
    except Exception as e:
        logger.error(f"Erro ao buscar '{query}': {e}")

    return results


def _parse_result(results: list[dict] | None, query: str, unidade: dict, servico: dict) -> dict:
    from urllib.parse import urlparse
    fox_pos = None
    concorrentes = []
    if results:
        for i, r in enumerate(results[:10], start=1):
            url = r.get("url", "")
            domain = urlparse(url).netloc.replace("www.", "")
            if "redefox.com.br" in domain:
                fox_pos = i
            else:
                if domain not in concorrentes:
                    concorrentes.append(domain)
    return {
        "query": query,
        "cidade": unidade["cidade"],
        "uf": unidade["uf"],
        "servico": servico["nome"],
        "linha": servico.get("linha", ""),
        "posicao_fox": fox_pos,
        "concorrente_1": concorrentes[0] if len(concorrentes) > 0 else None,
        "concorrente_2": concorrentes[1] if len(concorrentes) > 1 else None,
        "concorrente_3": concorrentes[2] if len(concorrentes) > 2 else None,
    }


def run():
    logger.info("Iniciando SERP Scanner...")
    quota = _load_quota()
    cache = _load_cache()

    # Grupo 1: Serviços por cidade
    queries_g1 = []
    for unidade in UNIDADES:
        for servico in SERVICOS:
            if any(l in unidade["linhas"] for l in servico["linhas"]):
                query = f"{servico['nome']} em {unidade['cidade']} {unidade['uf']}"
                queries_g1.append((query, unidade, servico))

    # Grupo 2: Medidas de pneus × top 5 cidades
    top5_cidades = [u for u in UNIDADES if u["cidade"] in
                    ["Manaus", "Porto Velho", "Ariquemes", "Ji-Paraná", "Vilhena"]]
    seen_cidades = set()
    cidades_unicas = []
    for u in top5_cidades:
        if u["cidade"] not in seen_cidades:
            seen_cidades.add(u["cidade"])
            cidades_unicas.append(u)

    servico_pneu = next((s for s in SERVICOS if s["slug"] == "pneus-geometria-3d"), SERVICOS[0])
    queries_g2 = []
    for medida in MEDIDAS_PNEUS_CHAVE[:5]:
        for unidade in cidades_unicas[:5]:
            query = f"pneu {medida} {unidade['cidade']}"
            queries_g2.append((query, unidade, {**servico_pneu, "nome": f"Pneu {medida}"}))

    all_queries = queries_g1 + queries_g2
    logger.info(f"Total de queries: {len(all_queries)}")

    records = []
    batch_size = 5

    for i in range(0, len(all_queries), batch_size):
        batch = all_queries[i:i + batch_size]
        with ThreadPoolExecutor(max_workers=batch_size) as pool:
            futures = {
                pool.submit(_do_search, q, quota, cache): (q, u, s)
                for q, u, s in batch
            }
            for future in as_completed(futures):
                query, unidade, servico = futures[future]
                try:
                    results = future.result()
                    records.append(_parse_result(results, query, unidade, servico))
                except Exception as e:
                    logger.error(f"Erro processando '{query}': {e}")
        _save_quota(quota)
        _save_cache(cache)
        time.sleep(1)

    if not records:
        logger.warning("SERP Scanner sem resultados.")
        return

    df = pd.DataFrame(records)
    df.to_csv("output/3_serp_concorrencia_local.csv", index=False, encoding="utf-8")
    logger.info(f"SERP: {len(df)} queries salvas.")

    # Calcular Share of Voice
    total_queries = len(df)
    fox_presente = df["posicao_fox"].notna().sum()
    share_of_voice = round((fox_presente / total_queries) * 100, 1) if total_queries > 0 else 0.0

    sov_data = {
        "share_of_voice_pct": share_of_voice,
        "fox_presente_em": int(fox_presente),
        "total_queries_monitoradas": total_queries,
        "data": datetime.now().strftime("%Y-%m-%d"),
    }
    import json as _json
    Path("output").mkdir(exist_ok=True)
    Path("output/share_of_voice.json").write_text(
        _json.dumps(sov_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Share of Voice: {share_of_voice}% ({fox_presente}/{total_queries} queries)")

    # Resumo de cotas no log
    logger.info("── Resumo de cotas SERP ──────────────────────")
    for p in sorted(SERP_PROVIDERS, key=lambda x: x["priority"]):
        limit = p["monthly_quota"]
        used = quota.get(p["name"], {}).get("used", 0)
        if limit >= 999_999:
            logger.info(f"  {p['name']:12} {used:>5} queries usadas  [overflow pago]")
        else:
            pct = int(used / limit * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            status = "⚠ ALERTA" if pct >= 80 else ("✅ OK" if pct < 60 else "🟡 ATENÇÃO")
            logger.info(f"  {p['name']:12} [{bar}] {pct:>3}%  {used}/{limit}  {status}")
    logger.info("──────────────────────────────────────────────")
