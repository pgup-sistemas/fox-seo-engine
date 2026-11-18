import logging
import os
import tempfile

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.matriz_negocio import GSC_PROPERTY, normalize_url

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/indexing",
]


def _get_credentials():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(creds_json)
            creds_path = f.name
        try:
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        finally:
            os.unlink(creds_path)
        return creds
    if os.path.exists("credentials.json"):
        return service_account.Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return None


def _probe_property(service, candidates: list[str]) -> str | None:
    for prop in candidates:
        try:
            service.searchanalytics().query(
                siteUrl=prop,
                body={"startDate": "2020-01-01", "endDate": "2020-01-02", "rowLimit": 1},
            ).execute()
            logger.info(f"Propriedade GSC válida: {prop}")
            with open("output/gsc_config.txt", "w", encoding="utf-8") as f:
                f.write(prop)
            return prop
        except Exception as e:
            logger.warning(f"Propriedade GSC '{prop}' falhou: {e}")
    return None


def run():
    logger.info("Iniciando GSC Auditor...")
    creds = _get_credentials()
    if not creds:
        logger.warning("Credenciais Google não encontradas. Pulando GSC Auditor.")
        return

    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    property_url = _probe_property(service, [GSC_PROPERTY, "https://redefox.com.br/"])
    if not property_url:
        logger.warning("Nenhuma propriedade GSC acessível. Pulando.")
        return

    rows = []
    start_row = 0
    batch_size = 25000
    while True:
        try:
            resp = service.searchanalytics().query(
                siteUrl=property_url,
                body={
                    "startDate": _days_ago(90),
                    "endDate": _days_ago(1),
                    "dimensions": ["page", "query"],
                    "rowLimit": batch_size,
                    "startRow": start_row,
                },
            ).execute()
        except Exception as e:
            logger.error(f"Erro ao consultar GSC: {e}")
            break

        batch = resp.get("rows", [])
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        start_row += batch_size

    if not rows:
        logger.warning("GSC não retornou dados. Arquivo não atualizado.")
        return

    records = []
    for row in rows:
        keys = row.get("keys", [])
        records.append({
            "page": normalize_url(keys[0]) if len(keys) > 0 else "",
            "query": keys[1] if len(keys) > 1 else "",
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0.0),
            "position": row.get("position", 0.0),
        })

    df = pd.DataFrame(records)
    df.to_csv("output/2_gsc_performance.csv", index=False, encoding="utf-8")
    logger.info(f"GSC: {len(df)} linhas salvas em output/2_gsc_performance.csv")


def _days_ago(n: int) -> str:
    from datetime import date, timedelta
    return (date.today() - timedelta(days=n)).strftime("%Y-%m-%d")
