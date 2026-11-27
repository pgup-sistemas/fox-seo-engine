"""
Cruzamento entre buscas reais no catálogo Fox (foxsitechat) e posicionamento no Google (SERP).

Consome GET /api/top-buscas-por-cidade do backend do catálogo e cruza com
output/3_serp_concorrencia_local.csv para identificar medidas que têm alta
demanda no catálogo mas a Fox não aparece no Top 10 do Google.

Salva em output/8_catalogo_vs_serp.csv e output/8_catalogo_insights.json.
"""

import json
import logging
import re
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

CATALOGO_URL = "https://foxsitechat.onrender.com/api/top-buscas-por-cidade"
OUT_CSV  = Path("output/8_catalogo_vs_serp.csv")
OUT_JSON = Path("output/8_catalogo_insights.json")

_CIDADE_NORMALIZA = {
    "manaus":      "Manaus",
    "porto velho": "Porto Velho",
    "ariquemes":   "Ariquemes",
    "ji-paraná":   "Ji-Paraná",
    "ji-parana":   "Ji-Paraná",
    "cacoal":      "Cacoal",
    "vilhena":     "Vilhena",
    "parintins":   "Parintins",
    "xapuri":      "Xapuri",
    "rio branco":  "Rio Branco",
}

_RE_ARO = re.compile(r'[Rr](\d{2})')
_RE_MEDIDA = re.compile(r'(\d{3})[/\\](\d{2})\s*[Rr](\d{2})')


def _normalizar_cidade(cidade: str) -> str:
    return _CIDADE_NORMALIZA.get(cidade.lower().strip(), cidade.strip().title())


def _medida_para_query(medida: str) -> str:
    """'185/65R15' → 'pneu 185/65R15' ou 'ARO 20' → 'pneu aro 20'."""
    medida = medida.strip().upper()
    m = _RE_MEDIDA.match(medida)
    if m:
        return f"pneu {m.group(1)}/{m.group(2)}R{m.group(3)}"
    m_aro = _RE_ARO.match(medida.replace("ARO", "").strip())
    if m_aro or medida.startswith("ARO"):
        num = medida.replace("ARO", "").strip()
        return f"pneu aro {num}"
    return f"pneu {medida}"


def _buscar_catalogo(dias: int = 30, limite_cidades: int = 10, limite_termos: int = 5) -> list[dict]:
    """Chama /api/top-buscas-por-cidade e retorna lista de {cidade, medida, total}."""
    try:
        resp = requests.get(
            CATALOGO_URL,
            params={"dias": dias, "limite_cidades": limite_cidades, "limite_termos": limite_termos},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Não foi possível acessar o catálogo: {e}")
        return []

    registros = []
    for item in data.get("cidades", []):
        cidade = _normalizar_cidade(item.get("cidade", ""))
        for termo in item.get("top_termos", []):
            medida = termo.get("medida", "").strip()
            if medida:
                registros.append({
                    "cidade_catalogo": cidade,
                    "medida": medida.upper(),
                    "buscas_catalogo": termo.get("total", 0),
                })
    return registros


def _carregar_serp() -> pd.DataFrame | None:
    path = Path("output/3_serp_concorrencia_local.csv")
    if not path.exists():
        logger.warning("output/3_serp_concorrencia_local.csv não encontrado.")
        return None
    try:
        return pd.read_csv(path, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Erro ao ler SERP CSV: {e}")
        return None


def run():
    logger.info("Iniciando Catalogo Insights...")

    registros_catalogo = _buscar_catalogo()
    if not registros_catalogo:
        logger.warning("Catalogo Insights: sem dados do catálogo — endpoint indisponível ou sem buscas.")
        _salvar_vazio()
        return

    df_cat = pd.DataFrame(registros_catalogo)
    df_serp = _carregar_serp()

    linhas = []
    for _, row in df_cat.iterrows():
        cidade   = row["cidade_catalogo"]
        medida   = row["medida"]
        buscas   = row["buscas_catalogo"]
        query_ref = _medida_para_query(medida)

        posicao_fox  = None
        gap          = True
        opp_score    = 0

        if df_serp is not None:
            # Procura no SERP uma query similar para aquela cidade
            mask = (
                df_serp["cidade"].str.lower() == cidade.lower()
            ) & (
                df_serp["query"].str.upper().str.contains(
                    medida.replace("/", r"[/\\]?").replace("R", "[Rr]?"), regex=True, na=False
                )
            )
            match = df_serp[mask]
            if not match.empty:
                posicao_fox = match.iloc[0].get("posicao_fox")
                opp_score   = match.iloc[0].get("oportunidade_score", 0)
                gap = pd.isna(posicao_fox) or posicao_fox is None

        # Prioridade: alto volume no catálogo + ausente no Google = ouro
        prioridade = "CRÍTICA" if (buscas >= 3 and gap) else \
                     "ALTA"    if (buscas >= 2 and gap) else \
                     "MÉDIA"   if gap else "OK"

        linhas.append({
            "cidade":           cidade,
            "medida":           medida,
            "buscas_catalogo":  buscas,
            "query_google_ref": f"{query_ref} {cidade}",
            "posicao_fox_google": posicao_fox,
            "gap_google":       gap,
            "oportunidade_score": opp_score,
            "prioridade":       prioridade,
        })

    df = pd.DataFrame(linhas)
    if df.empty:
        logger.warning("Catalogo Insights: DataFrame vazio após cruzamento.")
        _salvar_vazio()
        return

    df = df.sort_values(["prioridade", "buscas_catalogo"], ascending=[True, False])
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    logger.info(f"Catalogo Insights: {len(df)} cruzamentos salvos em {OUT_CSV}")

    # Resumo JSON para o dashboard
    criticas = df[df["prioridade"] == "CRÍTICA"]
    altas    = df[df["prioridade"] == "ALTA"]
    gaps     = df[df["gap_google"] == True]

    top5 = criticas.head(5)[
        ["cidade", "medida", "buscas_catalogo", "query_google_ref", "prioridade"]
    ].to_dict(orient="records")

    resumo = {
        "total_cruzamentos":   len(df),
        "gaps_google":         int(gaps.shape[0]),
        "prioridade_critica":  int(criticas.shape[0]),
        "prioridade_alta":     int(altas.shape[0]),
        "top5_oportunidades":  top5,
        "data":                pd.Timestamp.now().strftime("%Y-%m-%d"),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Resumo JSON salvo em {OUT_JSON}")


def _salvar_vazio():
    resumo = {
        "total_cruzamentos": 0,
        "gaps_google": 0,
        "prioridade_critica": 0,
        "prioridade_alta": 0,
        "top5_oportunidades": [],
        "data": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "nota": "Sem dados do catálogo nesta execução.",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
