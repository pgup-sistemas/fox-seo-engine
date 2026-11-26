"""
Script de validação da PLACES_API_KEY antes de rodar o pipeline completo.

Uso:
    python test_places_api.py AIza...suachave...

Ou com .env configurado:
    python test_places_api.py
"""
import os
import sys
import requests

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"

TEST_UNITS = [
    ("Fox Manaus", "Manaus"),
    ("Fox Nações Unidas", "Porto Velho"),
]


def test_key(key: str):
    print(f"\nTestando chave: {key[:8]}...{key[-4:]}\n")

    for nome, cidade in TEST_UNITS:
        print(f"  Buscando: {nome} em {cidade}")

        # Passo 1 — findplacefromtext
        r = requests.get(
            f"{PLACES_BASE}/findplacefromtext/json",
            params={
                "input": f"{nome} {cidade}",
                "inputtype": "textquery",
                "fields": "place_id,name",
                "key": key,
            },
            timeout=15,
        )

        body = r.json()
        status = body.get("status")

        if status == "REQUEST_DENIED":
            print(f"  ❌ REQUEST_DENIED — {body.get('error_message', 'billing não ativo ou API não habilitada')}")
            return False

        if status == "ZERO_RESULTS":
            print(f"  ⚠  ZERO_RESULTS — nome não encontrado no Maps (chave ok, mas unidade não cadastrada com esse nome)")
            continue

        if status != "OK":
            print(f"  ❌ Status inesperado: {status}")
            return False

        candidates = body.get("candidates", [])
        if not candidates:
            print(f"  ⚠  Sem candidatos")
            continue

        place_id = candidates[0]["place_id"]
        place_name = candidates[0].get("name", "?")
        print(f"  ✅ place_id: {place_id}  |  nome Maps: {place_name}")

        # Passo 2 — place/details
        r2 = requests.get(
            f"{PLACES_BASE}/details/json",
            params={
                "place_id": place_id,
                "fields": "rating,user_ratings_total",
                "key": key,
            },
            timeout=15,
        )
        result = r2.json().get("result", {})
        rating = result.get("rating", "N/A")
        total = result.get("user_ratings_total", "N/A")
        print(f"  ⭐ rating={rating}  |  total_avaliações={total}\n")

    print("✅ Chave válida. Reviews Monitor pronto para rodar.")
    return True


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PLACES_API_KEY", "")
    if not key:
        print("Erro: informe a chave como argumento ou defina PLACES_API_KEY no .env")
        sys.exit(1)
    ok = test_key(key)
    sys.exit(0 if ok else 1)
