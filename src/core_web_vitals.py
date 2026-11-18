import logging
import os
import time
from pathlib import Path

import pandas as pd
import requests

from config.matriz_negocio import DOMAIN, normalize_url

logger = logging.getLogger(__name__)

PSI_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
MAX_URLS = 10


def _get_top_urls() -> list[str]:
    urls = [normalize_url(DOMAIN + "/")]
    audit_path = Path("output/1_auditoria_tecnica_site.csv")
    if audit_path.exists():
        df = pd.read_csv(audit_path, encoding="utf-8")
        df = df[df["status_http"] == 200].copy()
        # Priorizar páginas de unidades
        unit_pages = df[df["url"].str.contains("/unidades/", na=False)]["url"].tolist()
        other_pages = df[~df["url"].str.contains("/unidades/", na=False)]["url"].tolist()
        candidates = unit_pages + other_pages
        for u in candidates:
            norm = normalize_url(u)
            if norm not in urls:
                urls.append(norm)
            if len(urls) >= MAX_URLS:
                break
    return urls[:MAX_URLS]


def _fetch_psi(url: str) -> dict | None:
    key = os.environ.get("PSI_API_KEY")
    params = {"url": url, "strategy": "mobile"}
    if key:
        params["key"] = key

    for attempt in range(2):
        try:
            resp = requests.get(PSI_BASE, params=params, timeout=60)
            if resp.status_code == 429:
                logger.warning(f"PSI rate limit para {url}, aguardando 60s...")
                time.sleep(60)
                continue
            resp.raise_for_status()
            data = resp.json()
            categories = data.get("lighthouseResult", {}).get("categories", {})
            audits = data.get("lighthouseResult", {}).get("audits", {})

            score = round(categories.get("performance", {}).get("score", 0) * 100)

            def _metric(key_name: str) -> float | None:
                a = audits.get(key_name, {})
                val = a.get("numericValue")
                return round(val / 1000, 2) if val else None

            lcp = _metric("largest-contentful-paint")
            cls_val = audits.get("cumulative-layout-shift", {}).get("numericValue")
            cls = round(cls_val, 3) if cls_val is not None else None
            inp = _metric("interaction-to-next-paint") or _metric("max-potential-fid")

            return {
                "url": url,
                "performance_score": score,
                "lcp_s": lcp,
                "cls": cls,
                "inp_s": inp,
            }
        except Exception as e:
            logger.warning(f"PSI erro para {url} (tentativa {attempt+1}): {e}")
    return None


def run():
    logger.info("Iniciando Core Web Vitals...")
    urls = _get_top_urls()
    logger.info(f"Medindo {len(urls)} URLs via PageSpeed Insights...")

    records = []
    for url in urls:
        result = _fetch_psi(url)
        if result:
            records.append(result)
            logger.info(f"PSI {url}: score={result['performance_score']}, LCP={result['lcp_s']}s")
        time.sleep(1)

    if not records:
        logger.warning("Core Web Vitals: sem dados (PSI indisponível).")
        return

    df = pd.DataFrame(records)
    df.to_csv("output/6_core_web_vitals.csv", index=False, encoding="utf-8")
    logger.info(f"Core Web Vitals: {len(df)} URLs salvas.")
