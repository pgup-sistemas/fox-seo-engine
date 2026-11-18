import logging
import re
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import extruct
import httpx
import pandas as pd
from bs4 import BeautifulSoup

from config.matriz_negocio import DOMAIN, normalize_url

logger = logging.getLogger(__name__)

USER_AGENT = "FoxSEOBot/1.0 (+https://github.com/redefox/fox-seo-engine)"
MAX_PAGES = 150
MAX_DEPTH = 3
MAX_WORKERS = 10


def _build_robot_parser(domain: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(f"{domain}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        logger.warning(f"Não foi possível ler robots.txt: {e}")
    return rp


def _fetch_sitemap_urls(domain: str, client: httpx.Client) -> list[str]:
    urls = []
    try:
        resp = client.get(f"{domain}/sitemap.xml")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml-xml")
        # sitemapindex recursivo
        for sitemap in soup.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc:
                try:
                    sub = client.get(loc.text.strip())
                    sub.raise_for_status()
                    sub_soup = BeautifulSoup(sub.text, "lxml-xml")
                    for url in sub_soup.find_all("url"):
                        l = url.find("loc")
                        if l:
                            urls.append(normalize_url(l.text.strip()))
                except Exception:
                    pass
        # urlset direto
        for url in soup.find_all("url"):
            l = url.find("loc")
            if l:
                urls.append(normalize_url(l.text.strip()))
    except Exception as e:
        logger.warning(f"Sitemap indisponível ({e}), usará crawling recursivo.")
    return list(set(urls))


def _count_words(soup: BeautifulSoup) -> int:
    text = " ".join(
        tag.get_text(" ", strip=True)
        for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"])
    )
    return len(re.findall(r"\w+", text))


def _classify_canonical(page_url: str, canonical_href: str | None) -> str:
    if not canonical_href:
        return "ausente"
    norm_page = normalize_url(page_url)
    norm_canon = normalize_url(canonical_href)
    if norm_page == norm_canon:
        return "auto"
    parsed_canon = urlparse(norm_canon)
    parsed_page = urlparse(norm_page)
    if parsed_canon.netloc != parsed_page.netloc:
        return "externo"
    return "externo"


def _fetch_page(url: str, client: httpx.Client, rp: RobotFileParser) -> dict:
    result = {
        "url": url,
        "status_http": None,
        "title": None,
        "meta_description": None,
        "h1": None,
        "canonical": None,
        "canonical_tipo": None,
        "contagem_palavras": 0,
        "tem_schema": False,
        "tipo_schema": None,
        "linkado_por": None,
        "erro": None,
    }
    if not rp.can_fetch(USER_AGENT, url):
        logger.debug(f"robots.txt bloqueia: {url}")
        result["erro"] = "robots_disallow"
        return result
    try:
        resp = client.get(url, follow_redirects=True)
        result["status_http"] = resp.status_code
        if resp.status_code != 200:
            return result
        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        try:
            title_tag = soup.find("title")
            result["title"] = title_tag.get_text(strip=True) if title_tag else None
        except Exception:
            pass

        try:
            meta = soup.find("meta", attrs={"name": "description"})
            result["meta_description"] = meta.get("content", "").strip() if meta else None
        except Exception:
            pass

        try:
            h1 = soup.find("h1")
            result["h1"] = h1.get_text(strip=True) if h1 else None
        except Exception:
            pass

        try:
            canon = soup.find("link", rel="canonical")
            href = canon.get("href", "").strip() if canon else None
            result["canonical"] = href
            result["canonical_tipo"] = _classify_canonical(url, href)
        except Exception:
            pass

        try:
            result["contagem_palavras"] = _count_words(soup)
        except Exception:
            pass

        try:
            schemas = extruct.extract(html, base_url=url, syntaxes=["json-ld"])
            for item in schemas.get("json-ld", []):
                tipo = item.get("@type", "")
                if tipo in ("AutoRepair", "LocalBusiness", "AutoDealer"):
                    result["tem_schema"] = True
                    result["tipo_schema"] = tipo
                    break
        except Exception:
            pass

    except Exception as e:
        result["erro"] = str(e)
    return result


def _extract_links(url: str, html: str, domain: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    parsed_domain = urlparse(domain).netloc
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(url, href)
        parsed = urlparse(full)
        if parsed.scheme in ("http", "https") and parsed.netloc == parsed_domain:
            links.append(normalize_url(full))
    return links


def run():
    logger.info("Iniciando crawler...")
    client = httpx.Client(
        http2=True,
        timeout=httpx.Timeout(connect=5.0, read=10.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
    rp = _build_robot_parser(DOMAIN)

    urls_to_crawl = _fetch_sitemap_urls(DOMAIN, client)
    if urls_to_crawl:
        logger.info(f"Sitemap: {len(urls_to_crawl)} URLs encontradas.")
    else:
        logger.info("Iniciando crawling recursivo...")
        urls_to_crawl = [normalize_url(DOMAIN + "/")]

    visited = set()
    queue = deque()
    referrers: dict[str, str] = {}
    depth_map: dict[str, int] = {}

    for u in urls_to_crawl:
        queue.append(u)
        depth_map[u] = 0

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        while queue and len(visited) < MAX_PAGES:
            batch = []
            while queue and len(batch) < MAX_WORKERS * 2:
                url = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)
                batch.append(url)

            futures = {pool.submit(_fetch_page, url, client, rp): url for url in batch}
            for future in as_completed(futures):
                url = futures[future]
                try:
                    data = future.result()
                except Exception as e:
                    logger.error(f"Erro ao crawlar {url}: {e}")
                    continue

                data["linkado_por"] = referrers.get(url)
                results.append(data)

                # Descobrir novos links para crawling recursivo
                depth = depth_map.get(url, 0)
                if depth < MAX_DEPTH and data.get("status_http") == 200:
                    try:
                        resp = client.get(url)
                        new_links = _extract_links(url, resp.text, DOMAIN)
                        for link in new_links:
                            if link not in visited and link not in depth_map:
                                depth_map[link] = depth + 1
                                referrers[link] = url
                                queue.append(link)
                    except Exception:
                        pass

    client.close()

    df = pd.DataFrame(results)
    if df.empty:
        logger.warning("Nenhuma URL crawlada. Pulando salvamento.")
        return

    # Enriquecer 404s com referrers
    df["linkado_por"] = df.apply(
        lambda r: referrers.get(r["url"], r["linkado_por"]), axis=1
    )

    df.to_csv("output/1_auditoria_tecnica_site.csv", index=False, encoding="utf-8")
    logger.info(f"Auditoria salva: {len(df)} páginas em output/1_auditoria_tecnica_site.csv")
