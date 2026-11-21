import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from config.matriz_negocio import (
    DOMAIN,
    SERVICOS,
    UNIDADES,
    normalize_url,
    slugify,
)

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len - 20:
        truncated = truncated[:last_space]
    return truncated.rstrip(" ,.") + "."


def _make_title(servico_nome: str, cidade: str, uf: str) -> str:
    suffix = f" | Rede Fox"
    base = f"{servico_nome} em {cidade} {uf}"
    if len(base + suffix) <= 60:
        return base + suffix
    # Truncar nome do serviço
    max_service = 60 - len(f" em {cidade} {uf}{suffix}")
    return f"{servico_nome[:max_service].rstrip()} em {cidade} {uf}{suffix}"


def _make_meta(servico_nome: str, cidade: str, linha: str, telefone: str) -> str:
    text = f"Fox {cidade}: {servico_nome} com qualidade garantida. Atendimento para {linha}. Ligue {telefone}."
    return _truncate(text, 155)


def _load_crawl() -> set[str]:
    path = Path("output/1_auditoria_tecnica_site.csv")
    if not path.exists():
        return set()
    df = pd.read_csv(path, encoding="utf-8")
    return {normalize_url(u) for u in df["url"].dropna().tolist()}


def _crawl_paths(existing_urls: set[str]) -> list[str]:
    """Extrai só o caminho (sem o domínio) de cada URL rastreada, para casar slugs."""
    paths = []
    for u in existing_urls:
        paths.append(u.split("/", 1)[1] if "/" in u else "")
    return paths


def _pagina_existe(servico_slug: str, cidade_slug: str, crawl_paths: list[str]) -> bool:
    """Considera a combinação cidade×serviço coberta quando alguma página do site
    contém, no caminho da URL, tanto o slug do serviço quanto o da cidade — em
    qualquer ordem, separador ou estrutura de pastas. Reconhece padrões como
    /servicos/pneus-geometria-3d-manaus, /manaus/pneus-geometria-3d,
    /servicos/manaus/pneus-geometria-3d, etc."""
    return any(servico_slug in p and cidade_slug in p for p in crawl_paths)


def run():
    logger.info("Iniciando Gap Analyzer...")
    existing_urls = _load_crawl()
    crawl_paths = _crawl_paths(existing_urls)

    records = []
    for unidade in UNIDADES:
        cidade_slug = slugify(unidade["cidade"])
        for servico in SERVICOS:
            if not any(l in unidade["linhas"] for l in servico["linhas"]):
                continue
            linha = "/".join(servico["linhas"])
            url_sugerida = normalize_url(
                f"{DOMAIN}/servicos/{servico['slug']}-{unidade['slug_cidade']}"
            )
            existe = (
                url_sugerida in existing_urls
                or _pagina_existe(servico["slug"], cidade_slug, crawl_paths)
            )
            status = "existe" if existe else "ausente"
            records.append({
                "Cidade": unidade["cidade"],
                "UF": unidade["uf"],
                "Unidade": unidade["nome"],
                "Linha": linha,
                "Servico": servico["nome"],
                "Status_Atual": status,
                "URL_Sugerida": url_sugerida,
                "Title_SEO": _make_title(servico["nome"], unidade["cidade"], unidade["uf"]),
                "Meta_Description": _make_meta(
                    servico["nome"], unidade["cidade"], linha, unidade["telefone"]
                ),
            })

    df = pd.DataFrame(records)
    if df.empty:
        logger.warning("Gap Analyzer: plano vazio.")
        return

    df.to_csv("output/4_plano_expansao_landing_pages.csv", index=False, encoding="utf-8")
    df.to_excel("output/4_plano_expansao.xlsx", index=False)
    logger.info(f"Plano de expansão: {len(df)} landing pages ({df[df['Status_Atual']=='ausente'].shape[0]} ausentes).")

    # Gerar lista de URLs para indexar
    urls_novas = df[df["Status_Atual"] != "existe"]["URL_Sugerida"].tolist()
    Path("output/urls_para_indexar.txt").write_text(
        "\n".join(urls_novas), encoding="utf-8"
    )
    logger.info(f"output/urls_para_indexar.txt: {len(urls_novas)} URLs.")

    # Schemas AutoRepair
    _gerar_schemas_autorepair()

    # Schemas FAQPage
    _gerar_schemas_faqpage(records)

    # Sitemap sugerido
    _gerar_sitemap(urls_novas)


def _gerar_schemas_autorepair():
    schemas = []
    for u in UNIDADES:
        servicos_unidade = [
            s for s in SERVICOS if any(l in u["linhas"] for l in s["linhas"])
        ]
        schemas.append({
            "@context": "https://schema.org",
            "@type": "AutoRepair",
            "name": u["nome"],
            "url": f"{DOMAIN}/unidades/{u['slug_cidade']}",
            "telephone": u["telefone"],
            "address": {
                "@type": "PostalAddress",
                "streetAddress": u["endereco"],
                "addressLocality": u["cidade"],
                "addressRegion": u["uf"],
                "addressCountry": "BR",
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": u["lat"],
                "longitude": u["lng"],
            },
            "openingHours": u["horario"],
            "paymentAccepted": "Dinheiro, Cartão de Crédito, Cartão de Débito, PIX",
            "priceRange": "$$",
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "Serviços Automotivos",
                "itemListElement": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["nome"]}}
                    for s in servicos_unidade
                ],
            },
        })
    Path("output/5_schemas_jsonld_sugeridos.json").write_text(
        json.dumps(schemas, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Schemas AutoRepair: {len(schemas)} unidades.")


def _gerar_schemas_faqpage(records: list[dict]):
    faq_schemas = []
    for r in records:
        if r["Status_Atual"] == "existe":
            continue
        s_nome = r["Servico"]
        cidade = r["Cidade"]
        telefone = next(
            (u["telefone"] for u in UNIDADES if u["cidade"] == cidade), ""
        )
        horario = next(
            (u["horario"] for u in UNIDADES if u["cidade"] == cidade), ""
        )
        faq_schemas.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "url": r["URL_Sugerida"],
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"Quanto custa {s_nome} em {cidade}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"O preço de {s_nome} na Fox {cidade} varia conforme o veículo. Ligue {telefone} para orçamento sem compromisso.",
                    },
                },
                {
                    "@type": "Question",
                    "name": f"Quanto tempo leva {s_nome} na Fox {cidade}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"O serviço de {s_nome} na Fox {cidade} leva em média 1 a 2 horas, dependendo do veículo. Atendemos {horario}.",
                    },
                },
                {
                    "@type": "Question",
                    "name": f"A Fox {cidade} oferece garantia em {s_nome}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"Sim. Todos os serviços da Rede Fox têm garantia. Consulte nosso time em {telefone}.",
                    },
                },
            ],
        })
    Path("output/5b_schemas_faqpage_sugeridos.json").write_text(
        json.dumps(faq_schemas, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Schemas FAQPage: {len(faq_schemas)} landing pages.")


def _gerar_sitemap(urls: list[str]):
    today = date.today().strftime("%Y-%m-%d")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines += [
            "  <url>",
            f"    <loc>{url}</loc>",
            "    <changefreq>monthly</changefreq>",
            "    <priority>0.8</priority>",
            f"    <lastmod>{today}</lastmod>",
            "  </url>",
        ]
    lines.append("</urlset>")
    Path("output/sitemap_sugerido.xml").write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Sitemap sugerido: {len(urls)} URLs.")
