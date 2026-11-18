# fox-seo-engine

Sistema de auditoria, expansão e aceleração de indexação SEO para o portal da Rede Fox (`redefox.com.br`).

Executa automaticamente toda segunda-feira via GitHub Actions e publica um Dashboard Executivo em GitHub Pages.

![SEO Audit](https://github.com/redefox/fox-seo-engine/actions/workflows/seo_audit_pipeline.yml/badge.svg)

---

## Arquitetura

```
Crawl do site → GSC API → SERP (4 provedores) → Core Web Vitals
       ↓               ↓              ↓                  ↓
  Gap Analyzer ─────────────────────────────────────────→ Reviews Monitor
       ↓
  Indexing Pusher → IndexNow + Google API + Sitemap ping
       ↓
  Dashboard Builder → docs/index.html (GitHub Pages)
```

**Módulos:**

| Arquivo | Função | Output |
|---|---|---|
| `crawler_site.py` | Crawl técnico do site | `output/1_auditoria_tecnica_site.csv` |
| `gsc_auditor.py` | Dados do Google Search Console | `output/2_gsc_performance.csv` |
| `serp_scanner.py` | Posição nos resultados locais + Share of Voice | `output/3_serp_concorrencia_local.csv` |
| `gap_analyzer.py` | Plano de expansão + schemas JSON-LD + FAQ | `output/4_*`, `output/5_*`, `output/5b_*` |
| `reviews_monitor.py` | Avaliações Google por unidade (opcional) | `output/7_reviews_monitor.csv` |
| `indexing_pusher.py` | Envio de URLs para IndexNow/Google | — |
| `core_web_vitals.py` | LCP, CLS, INP via PageSpeed Insights | `output/6_core_web_vitals.csv` |
| `dashboard_builder.py` | Dashboard executivo estático | `docs/index.html` |

---

## Configuração de Secrets

Em **Settings → Secrets and variables → Actions**, adicione:

| Secret | Obrigatório | Descrição |
|---|---|---|
| `GOOGLE_CREDENTIALS_JSON` | Sim | JSON completo da Service Account (GSC + Indexing API) |
| `BRAVE_SEARCH_KEY` | Recomendado | Brave Search API — 2.000 queries/mês FREE |
| `BING_SEARCH_KEY` | Recomendado | Bing Web Search v7 — 1.000 queries/mês FREE |
| `TAVILY_API_KEY` | Recomendado | Tavily Search API — 1.000 queries/mês FREE |
| `DATAFORSEO_LOGIN` | Opcional | Base64 de "login:password" — overflow pago ($0,0006/query) |
| `INDEXNOW_KEY` | Recomendado | Chave IndexNow — indexação instantânea no Bing/Yandex |
| `PSI_API_KEY` | Opcional | PageSpeed Insights — aumenta rate limit para 400 req/dia |
| `PLACES_API_KEY` | Opcional | Google Places API — monitoramento de avaliações das unidades |

> **Orçamento SERP:** Brave + Bing + Tavily = 4.000 queries gratuitas/mês. Pipeline usa ~520/mês (87% de margem). DataForSEO só é acionado como overflow.

---

## Ativar GitHub Pages

1. **Settings → Pages**
2. Source: `Deploy from a branch`
3. Branch: `main` / folder: `/docs`
4. Salvar — URL gerada: `https://{owner}.github.io/{repo}/`

---

## Execução Local

```bash
cp .env.example .env
# Editar .env com suas chaves
pip install -r requirements.txt
python main.py
```

---

## Outputs

| Arquivo | Descrição |
|---|---|
| `output/1_auditoria_tecnica_site.csv` | Auditoria técnica de todas as páginas crawladas |
| `output/2_gsc_performance.csv` | Performance GSC dos últimos 90 dias |
| `output/3_serp_concorrencia_local.csv` | Posição da Fox em 155+ buscas locais |
| `output/4_plano_expansao_landing_pages.csv` | Landing pages a criar com title/meta prontos |
| `output/4_plano_expansao.xlsx` | Plano de expansão em Excel para download |
| `output/5_schemas_jsonld_sugeridos.json` | Schemas AutoRepair para cada unidade |
| `output/5b_schemas_faqpage_sugeridos.json` | Schemas FAQPage para cada landing page |
| `output/6_core_web_vitals.csv` | LCP, CLS, INP mobile das 10 principais páginas |
| `output/7_reviews_monitor.csv` | Avaliações Google + alertas por unidade |
| `output/share_of_voice.json` | % de buscas onde a Fox aparece no Top 10 |
| `output/sitemap_sugerido.xml` | Sitemap com todas as URLs do plano de expansão |
| `output/urls_para_indexar.txt` | URLs novas para envio ao IndexNow |
| `output/historico_evolucao.csv` | Histórico semanal de todos os KPIs |
| `output/RELATORIO_EXECUTIVO.md` | Relatório executivo em Markdown |
| `docs/index.html` | Dashboard interativo — publicado via GitHub Pages |
