import logging
import os
import tempfile
from pathlib import Path

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

INDEXNOW_URL = "https://api.indexnow.org/indexnow"
INDEXNOW_HOST = "redefox.com.br"


def _get_credentials():
    scopes = ["https://www.googleapis.com/auth/indexing"]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(creds_json)
            path = f.name
        try:
            creds = service_account.Credentials.from_service_account_file(path, scopes=scopes)
        finally:
            os.unlink(path)
        return creds
    if os.path.exists("credentials.json"):
        return service_account.Credentials.from_service_account_file("credentials.json", scopes=scopes)
    return None


def run():
    urls_file = Path("output/urls_para_indexar.txt")
    if not urls_file.exists() or urls_file.stat().st_size == 0:
        logger.info("output/urls_para_indexar.txt vazio ou ausente. Pulando indexação.")
        _ping_sitemap()
        return

    urls = [u.strip() for u in urls_file.read_text(encoding="utf-8").splitlines() if u.strip()]
    if not urls:
        logger.info("Nenhuma URL para indexar.")
        _ping_sitemap()
        return

    logger.info(f"Indexing Pusher: {len(urls)} URLs para processar.")

    # Mecanismo 1: IndexNow
    _send_indexnow(urls)

    # Mecanismo 2: Google Indexing API (somente schemas válidos)
    _send_google_indexing(urls)

    # Mecanismo 3: Sitemap ping
    _ping_sitemap()


def _send_indexnow(urls: list[str]):
    key = os.environ.get("INDEXNOW_KEY")
    if not key:
        logger.info("INDEXNOW_KEY não configurado. Pulando IndexNow.")
        return
    batch_size = 100
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        try:
            resp = requests.post(
                INDEXNOW_URL,
                json={
                    "host": INDEXNOW_HOST,
                    "key": key,
                    "keyLocation": f"https://{INDEXNOW_HOST}/{key}.txt",
                    "urlList": batch,
                },
                timeout=30,
            )
            logger.info(f"IndexNow: lote {i//batch_size + 1} → HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"IndexNow erro: {e}")


def _send_google_indexing(urls: list[str]):
    # Verificar quais URLs têm schema no CSV de auditoria
    schema_urls = set()
    audit_path = Path("output/1_auditoria_tecnica_site.csv")
    if audit_path.exists():
        import pandas as pd
        df = pd.read_csv(audit_path, encoding="utf-8")
        eligible_types = {"JobPosting", "BroadcastEvent"}
        schema_urls = set(
            df[df["tipo_schema"].isin(eligible_types)]["url"].dropna().tolist()
        )

    eligible = [u for u in urls if u in schema_urls]
    if not eligible:
        logger.info("Nenhuma URL elegível para Google Indexing API (requer JobPosting/BroadcastEvent).")
        return

    creds = _get_credentials()
    if not creds:
        logger.warning("Credenciais Google não encontradas. Pulando Google Indexing API.")
        return

    service = build("indexing", "v3", credentials=creds, cache_discovery=False)
    for url in eligible[:200]:
        try:
            service.urlNotifications().publish(
                body={"url": url, "type": "URL_UPDATED"}
            ).execute()
            logger.info(f"Google Indexing API: {url}")
        except Exception as e:
            logger.warning(f"Google Indexing API falhou para {url}: {e}")


def _ping_sitemap():
    sitemap_url = "https://redefox.com.br/sitemap.xml"
    try:
        resp = requests.get(
            "https://www.google.com/ping",
            params={"sitemap": sitemap_url},
            timeout=30,
        )
        logger.info(f"Sitemap ping → HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Sitemap ping falhou: {e}")
