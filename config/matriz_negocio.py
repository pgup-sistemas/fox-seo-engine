import re
import unicodedata
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

DOMAIN = "https://redefox.com.br"
GSC_PROPERTY = "sc-domain:redefox.com.br"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def normalize_url(url: str) -> str:
    if not url:
        return url
    url = url.strip().lower()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    elif not url.startswith("https://"):
        url = "https://" + url
    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # Remove UTM and tracking params
    _REMOVE = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
               "fbclid", "gclid", "msclkid", "ref", "_ga"}
    qs = {k: v for k, v in parse_qs(parsed.query).items() if k not in _REMOVE}
    new_query = urlencode(qs, doseq=True)
    path = parsed.path.rstrip("/") or "/"
    clean = urlunparse((parsed.scheme, netloc, path, parsed.params, new_query, ""))
    return clean


UNIDADES = [
    {
        "nome": "Fox Manaus",
        "cidade": "Manaus",
        "uf": "AM",
        "slug_cidade": "manaus",
        "endereco": "Av. Tarumã, 700, Praça 14 de Janeiro",
        "telefone": "(92) 3622-7777",
        "linhas": ["carros", "caminhoes"],
        "lat": -3.1190,
        "lng": -60.0217,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Jorge Teixeira",
        "cidade": "Porto Velho",
        "uf": "RO",
        "slug_cidade": "porto-velho-jorge-teixeira",
        "endereco": "Av. Gov. Jorge Teixeira, 1159",
        "telefone": "(69) 3217-3040",
        "linhas": ["carros"],
        "lat": -8.7612,
        "lng": -63.9004,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Nações Unidas",
        "cidade": "Porto Velho",
        "uf": "RO",
        "slug_cidade": "porto-velho-nacoes-unidas",
        "endereco": "Av. Nações Unidas, 805",
        "telefone": "(69) 3217-3030",
        "linhas": ["carros"],
        "lat": -8.7489,
        "lng": -63.8850,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Recapagem Porto Velho",
        "cidade": "Porto Velho",
        "uf": "RO",
        "slug_cidade": "porto-velho-recapagem",
        "endereco": "Rua da Beira, 9400",
        "telefone": "(69) 3217-8800",
        "linhas": ["caminhoes"],
        "lat": -8.7700,
        "lng": -63.9100,
        "horario": "Mo-Fr 07:00-17:00",
    },
    {
        "nome": "Fox Ariquemes",
        "cidade": "Ariquemes",
        "uf": "RO",
        "slug_cidade": "ariquemes",
        "endereco": "Av. Canaã, 1717",
        "telefone": "(69) 3535-3270",
        "linhas": ["carros", "caminhoes"],
        "lat": -9.9122,
        "lng": -63.0338,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Ji-Paraná",
        "cidade": "Ji-Paraná",
        "uf": "RO",
        "slug_cidade": "ji-parana",
        "endereco": "Av. Transcontinental, 2444",
        "telefone": "(69) 3422-2711",
        "linhas": ["carros", "caminhoes"],
        "lat": -10.8824,
        "lng": -61.9469,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Cacoal",
        "cidade": "Cacoal",
        "uf": "RO",
        "slug_cidade": "cacoal",
        "endereco": "Av. Castelo Branco, 19558",
        "telefone": "(69) 3441-2384",
        "linhas": ["carros", "caminhoes"],
        "lat": -11.4358,
        "lng": -61.4474,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Vilhena Carros",
        "cidade": "Vilhena",
        "uf": "RO",
        "slug_cidade": "vilhena-carros",
        "endereco": "Av. Marechal Rondon, 3224",
        "telefone": "(69) 3321-4155",
        "linhas": ["carros"],
        "lat": -12.7406,
        "lng": -60.1458,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
    {
        "nome": "Fox Vilhena Caminhões",
        "cidade": "Vilhena",
        "uf": "RO",
        "slug_cidade": "vilhena-caminhoes",
        "endereco": "Av. Marechal Rondon, 7940",
        "telefone": "(69) 3322-3365",
        "linhas": ["caminhoes"],
        "lat": -12.7500,
        "lng": -60.1550,
        "horario": "Mo-Fr 07:00-17:00",
    },
    {
        "nome": "Fox Rio Branco",
        "cidade": "Rio Branco",
        "uf": "AC",
        "slug_cidade": "rio-branco",
        "endereco": "Via Chico Mendes, 1473",
        "telefone": "(68) 3221-2271",
        "linhas": ["carros", "caminhoes"],
        "lat": -9.9754,
        "lng": -67.8249,
        "horario": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    },
]

SERVICOS = [
    {"nome": "Pneus e Geometria 3D", "slug": "pneus-geometria-3d", "linhas": ["carros"]},
    {"nome": "Alinhamento e Balanceamento", "slug": "alinhamento-balanceamento", "linhas": ["carros"]},
    {"nome": "Suspensão e Amortecedores", "slug": "suspensao-amortecedores", "linhas": ["carros"]},
    {"nome": "Sistema de Freios", "slug": "sistema-freios", "linhas": ["carros"]},
    {"nome": "Troca de Óleo e Filtros", "slug": "troca-oleo-filtros", "linhas": ["carros"]},
    {"nome": "Baterias Automotivas", "slug": "baterias-automotivas", "linhas": ["carros"]},
    {"nome": "Ar Condicionado Automotivo", "slug": "ar-condicionado-automotivo", "linhas": ["carros"]},
    {"nome": "Injeção Eletrônica e Scanner", "slug": "injecao-eletronica-scanner", "linhas": ["carros"]},
    {"nome": "Sistema de Arrefecimento", "slug": "sistema-arrefecimento", "linhas": ["carros"]},
    {"nome": "Fluido de Câmbio Automático", "slug": "fluido-cambio-automatico", "linhas": ["carros"]},
    {"nome": "Recapagem de Pneus", "slug": "recapagem-pneus", "linhas": ["caminhoes"]},
    {"nome": "Alinhamento de Caminhões e Carretas", "slug": "alinhamento-caminhoes-carretas", "linhas": ["caminhoes"]},
    {"nome": "Pneus Agrícolas e OTR", "slug": "pneus-agricolas-otr", "linhas": ["caminhoes"]},
]

MEDIDAS_PNEUS_CHAVE = [
    "175/70 R14",
    "185/65 R15",
    "195/65 R15",
    "205/55 R16",
    "205/60 R16",
    "215/60 R17",
    "265/65 R17",
    "265/70 R17",
    "275/65 R18",
    "295/80 R22.5",
]

SERP_PROVIDERS = [
    {
        "name": "brave",
        "env_key": "BRAVE_SEARCH_KEY",
        "monthly_quota": 2000,
        "cost_per_query_usd": 0.0,
        "priority": 1,
    },
    {
        "name": "bing",
        "env_key": "BING_SEARCH_KEY",
        "monthly_quota": 1000,
        "cost_per_query_usd": 0.0,
        "priority": 2,
    },
    {
        "name": "tavily",
        "env_key": "TAVILY_API_KEY",
        "monthly_quota": 1000,
        "cost_per_query_usd": 0.0,
        "priority": 3,
    },
    {
        "name": "dataforseo",
        "env_key": "DATAFORSEO_LOGIN",
        "monthly_quota": 999_999,
        "cost_per_query_usd": 0.0006,
        "priority": 4,
    },
]
