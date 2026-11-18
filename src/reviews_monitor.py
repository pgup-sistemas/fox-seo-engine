import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from config.matriz_negocio import UNIDADES

logger = logging.getLogger(__name__)

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


def _find_place_id(nome: str, cidade: str, key: str) -> str | None:
    try:
        resp = requests.get(
            f"{PLACES_BASE}/findplacefromtext/json",
            params={
                "input": f"{nome} {cidade}",
                "inputtype": "textquery",
                "fields": "place_id",
                "key": key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        return candidates[0]["place_id"] if candidates else None
    except Exception as e:
        logger.warning(f"Erro ao buscar place_id para '{nome}': {e}")
        return None


def _get_place_details(place_id: str, key: str) -> dict:
    try:
        resp = requests.get(
            f"{PLACES_BASE}/details/json",
            params={
                "place_id": place_id,
                "fields": "rating,user_ratings_total",
                "key": key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception as e:
        logger.warning(f"Erro ao buscar detalhes do place '{place_id}': {e}")
        return {}


def _load_previous() -> dict:
    path = Path("output/7_reviews_monitor.csv")
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, encoding="utf-8")
        return {row["unidade"]: row["total_avaliacoes"] for _, row in df.iterrows()}
    except Exception:
        return {}


def _classify_status(rating: float | None, delta: int) -> str:
    if rating is None:
        return "SEM_DADOS"
    if rating < 4.0:
        return "ALERTA"
    if delta == 0:
        return "ESTAGNADO"
    if rating < 4.5:
        return "ATENÇÃO"
    return "OK"


def run():
    key = os.environ.get("PLACES_API_KEY")
    if not key:
        logger.info("PLACES_API_KEY não configurado. Pulando Reviews Monitor.")
        return

    logger.info("Iniciando Reviews Monitor...")
    previous = _load_previous()
    records = []

    for unidade in UNIDADES:
        place_id = _find_place_id(unidade["nome"], unidade["cidade"], key)
        time.sleep(0.2)

        rating = None
        total = 0
        if place_id:
            details = _get_place_details(place_id, key)
            rating = details.get("rating")
            total = details.get("user_ratings_total", 0)
            time.sleep(0.2)

        prev_total = previous.get(unidade["nome"], total)
        delta = total - prev_total if total else 0
        status = _classify_status(rating, delta)

        records.append({
            "unidade": unidade["nome"],
            "cidade": unidade["cidade"],
            "uf": unidade["uf"],
            "place_id": place_id,
            "rating": rating,
            "total_avaliacoes": total,
            "delta_avaliacoes": delta,
            "status": status,
            "data_coleta": date.today().isoformat(),
        })

        if status in ("ALERTA", "ESTAGNADO"):
            logger.warning(
                f"[{status}] {unidade['nome']}: rating={rating}, total={total}, delta={delta}"
            )

    df = pd.DataFrame(records)
    if df.empty:
        logger.warning("Reviews Monitor: sem dados.")
        return

    df.to_csv("output/7_reviews_monitor.csv", index=False, encoding="utf-8")
    alertas = df[df["status"].isin(["ALERTA", "ESTAGNADO"])].shape[0]
    logger.info(f"Reviews Monitor: {len(df)} unidades auditadas, {alertas} alertas.")
