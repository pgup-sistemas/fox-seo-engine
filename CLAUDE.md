Atue como um Engenheiro de Software Sênior, Arquiteto de Dados e Especialista em Technical SEO. Crie do zero neste repositório um sistema completo, modular, 100% automatizado e livre de manutenção em Python chamado `fox-seo-engine` para auditar, expandir e acelerar a indexação na web do portal da Rede Fox (`https://redefox.com.br`).

O sistema será executado automaticamente via GitHub Actions toda semana e gerará um Dashboard Executivo Web interativo e estático em `docs/index.html` (para publicação direta via GitHub Pages), além dos relatórios de dados em `output/`.

Crie toda a estrutura de arquivos e implemente o código funcional completo seguindo exatamente estas especificações:

---

### 1. Estrutura de Diretórios

```text
.
├── .github/
│   └── workflows/
│       └── seo_audit_pipeline.yml
├── config/
│   ├── __init__.py          ← obrigatório para importações funcionarem
│   └── matriz_negocio.py
├── src/
│   ├── __init__.py
│   ├── crawler_site.py
│   ├── gsc_auditor.py
│   ├── serp_scanner.py
│   ├── gap_analyzer.py
│   ├── reviews_monitor.py   ← monitoramento Google Reviews (requer PLACES_API_KEY)
│   ├── indexing_pusher.py
│   ├── core_web_vitals.py
│   └── dashboard_builder.py
├── output/
│   └── .gitkeep
├── docs/
│   └── .gitkeep
├── .cache/
│   └── .gitkeep             ← cache SERP local, não commitado
├── .env.example             ← template de variáveis para dev local
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

> `config/__init__.py` deve existir como arquivo vazio. Sem ele, `from config.matriz_negocio import slugify` falha com `ModuleNotFoundError` em alguns contextos de execução.

---

### 2. Especificação dos Arquivos e Módulos

#### 2.1 `requirements.txt`

Fixe **todas** as versões, incluindo as dependências transitivas críticas do `extruct`:

```
requests==2.32.3
httpx==0.27.0
beautifulsoup4==4.12.3
lxml==4.9.4
pandas==2.2.2
google-api-python-client==2.137.0
google-auth==2.32.0
duckduckgo-search==5.3.1b1
extruct==0.17.0
mf2py==1.1.3
html-text==0.5.2
w3lib==2.2.1
plotly==5.22.0
jinja2==3.1.4
python-dotenv==1.0.1
openpyxl==3.1.5
tenacity==8.5.0
```

**Notas de versão obrigatórias:**
- `duckduckgo-search==5.3.1b1` — última versão com API estável. Versões 6.x mudaram `DDGS().text()` para retornar um **gerador**, não uma lista, quebrando a detecção de resposta vazia. Nunca atualizar sem testar.
- `httpx` — substitui `requests` no crawler para suporte a HTTP/2 e timeouts granulares (connect + read separados).
- `mf2py` e `html-text` — dependências transitivas do `extruct` que se não fixadas podem conflitar com `lxml==4.9.4`.
- `tenacity` — retry com backoff exponencial e jitter. Nunca usar `time.sleep(2**n)` manual.
- `openpyxl` — usado por `pandas.DataFrame.to_excel()` para gerar `output/4_plano_expansao.xlsx`. O DataTables Buttons gera o .xlsx **client-side** via JSZip no browser — openpyxl não tem relação com o DataTables.

---

#### 2.2 `.env.example`

```ini
# Google Search Console + Indexing API (Service Account JSON completo)
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}

# ── SERP: rotação entre 4 provedores (divide and conquer) ─────────────────────
# Brave Search API — 2.000 queries/mês FREE · cadastro: api.search.brave.com
BRAVE_SEARCH_KEY=your_brave_key_here

# Bing Web Search v7 (Azure F0) — 1.000 queries/mês FREE · Azure Portal, sem cobrança
BING_SEARCH_KEY=your_bing_key_here

# Tavily Search API — 1.000 queries/mês FREE · cadastro: tavily.com
TAVILY_API_KEY=your_tavily_key_here

# DataForSEO — overflow only, $0.0006/query · depósito mínimo $1 cobre 3+ meses
# Formato: "login:password" codificado em base64
DATAFORSEO_LOGIN=your_dataforseo_login_base64_here

# ── Outros ────────────────────────────────────────────────────────────────────
# IndexNow — indexação instantânea no Bing/Yandex (gerar em https://www.indexnow.org/)
INDEXNOW_KEY=your_indexnow_key_here

# PageSpeed Insights API — aumenta rate limit de 25 para 400 req/dia (Google Cloud, free tier)
PSI_API_KEY=your_psi_api_key_here

# Google Places API — monitoramento de avaliações (reviews_monitor.py)
# 200 req/dia FREE · Google Cloud Console, mesmo projeto da Service Account
# Sem esta chave o módulo é ignorado sem afetar o restante do pipeline
PLACES_API_KEY=your_places_api_key_here
```

---

#### 2.3 `config/__init__.py`

Arquivo vazio. Obrigatório para que `config/` seja tratado como pacote Python.

---

#### 2.4 `config/matriz_negocio.py`

- Defina `DOMAIN = "https://redefox.com.br"` e `GSC_PROPERTY = "sc-domain:redefox.com.br"`.

- Implemente `slugify(text: str) -> str` usando `unicodedata.normalize('NFKD')` + `re.sub(r'[^a-z0-9]+', '-', ...).strip('-')`. Esta é a **única implementação** no projeto — todos os módulos importam daqui, nunca duplicar a lógica.

- Implemente `normalize_url(url: str) -> str` que: força `https://`, remove `www.`, remove trailing slash, remove parâmetros UTM/fbclid/gclid, faz lowercase. Usada em **todos** os merges de DataFrames para evitar linhas duplicadas por variações de protocolo.

- Cadastre as 10 unidades com os campos: `nome`, `cidade`, `uf`, `slug_cidade`, `endereco`, `telefone`, `linhas` (lista), `lat`, `lng`, `horario`:

  | Unidade | Cidade | UF | Endereço | Telefone | Linhas | Lat | Lng | Horário |
  |---|---|---|---|---|---|---|---|---|
  | Fox Manaus | Manaus | AM | Av. Tarumã, 700, Praça 14 de Janeiro | (92) 3622-7777 | carros, caminhoes | -3.1190 | -60.0217 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Jorge Teixeira | Porto Velho | RO | Av. Gov. Jorge Teixeira, 1159 | (69) 3217-3040 | carros | -8.7612 | -63.9004 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Nações Unidas | Porto Velho | RO | Av. Nações Unidas, 805 | (69) 3217-3030 | carros | -8.7489 | -63.8850 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Recapagem Porto Velho | Porto Velho | RO | Rua da Beira, 9400 | (69) 3217-8800 | caminhoes | -8.7700 | -63.9100 | Mo-Fr 07:00-17:00 |
  | Fox Ariquemes | Ariquemes | RO | Av. Canaã, 1717 | (69) 3535-3270 | carros, caminhoes | -9.9122 | -63.0338 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Ji-Paraná | Ji-Paraná | RO | Av. Transcontinental, 2444 | (69) 3422-2711 | carros, caminhoes | -10.8824 | -61.9469 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Cacoal | Cacoal | RO | Av. Castelo Branco, 19558 | (69) 3441-2384 | carros, caminhoes | -11.4358 | -61.4474 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Vilhena Carros | Vilhena | RO | Av. Marechal Rondon, 3224 | (69) 3321-4155 | carros | -12.7406 | -60.1458 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |
  | Fox Vilhena Caminhões | Vilhena | RO | Av. Marechal Rondon, 7940 | (69) 3322-3365 | caminhoes | -12.7500 | -60.1550 | Mo-Fr 07:00-17:00 |
  | Fox Rio Branco | Rio Branco | AC | Via Chico Mendes, 1473 | (68) 3221-2271 | carros, caminhoes | -9.9754 | -67.8249 | Mo-Fr 08:00-18:00, Sa 08:00-12:00 |

  > Para unidades duplicadas na mesma cidade, usar `slug_cidade` composto: `"vilhena-carros"` e `"vilhena-caminhoes"`. Porto Velho tem 3 unidades — usar `"porto-velho-jorge-teixeira"`, `"porto-velho-nacoes-unidas"`, `"porto-velho-recapagem"`.

- Cadastre `SERVICOS` com `nome`, `slug`, `linhas`:

  **Linha carros:** pneus-geometria-3d, alinhamento-balanceamento, suspensao-amortecedores, sistema-freios, troca-oleo-filtros, baterias-automotivas, ar-condicionado-automotivo, injecao-eletronica-scanner, sistema-arrefecimento, fluido-cambio-automatico.

  **Linha caminhoes:** recapagem-pneus, alinhamento-caminhoes-carretas, pneus-agricolas-otr.

- Defina `MEDIDAS_PNEUS_CHAVE`:
  `["175/70 R14", "185/65 R15", "195/65 R15", "205/55 R16", "205/60 R16", "215/60 R17", "265/65 R17", "265/70 R17", "275/65 R18", "295/80 R22.5"]`

- Defina `SERP_PROVIDERS` — lista ordenada por prioridade. O `serp_scanner` percorre esta lista sequencialmente, usando o próximo quando a cota mensal do atual se esgota:

  ```python
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
          "env_key": "DATAFORSEO_LOGIN",   # "login:password" em base64
          "monthly_quota": 999_999,         # ilimitado — overflow pago
          "cost_per_query_usd": 0.0006,
          "priority": 4,
      },
  ]
  ```

  > **Orçamento total gratuito:** Brave (2.000) + Bing (1.000) + Tavily (1.000) = **4.000 queries/mês**. Pipeline usa ~520/mês = 87% de margem. DataForSEO só é acionado se todas as cotas gratuitas esgotarem no mesmo mês; custo máximo = 520 × $0.0006 = **R$1,55/mês**.

---

#### 2.5 `src/crawler_site.py`

- Verificar `robots.txt` antes de crawlar: usar `urllib.robotparser.RobotFileParser` da stdlib. Definir User-Agent: `"FoxSEOBot/1.0 (+https://github.com/redefox/fox-seo-engine)"`. Respeitar `Disallow` — se uma URL for proibida, registrar em log e pular.

- Ler o `sitemap.xml` em `{DOMAIN}/sitemap.xml` suportando `<urlset>` e `<sitemapindex>` recursivo. Se falhar, fazer crawling recursivo com `max_pages=150`, `max_depth=3`.

- **Crawling concorrente obrigatório:** usar `concurrent.futures.ThreadPoolExecutor(max_workers=10)`. Com 150 páginas e 10 workers, o tempo cai de ~75 minutos (sequencial) para ~8 minutos. Usar `httpx.Client(http2=True, timeout=httpx.Timeout(connect=5.0, read=10.0))` dentro do pool.

- Deduplicar URLs com `normalize_url()` de `config.matriz_negocio` antes de enfileirar.

- Para cada URL, extrair com `try/except` **individual por campo**:
  - Status HTTP
  - `<title>`
  - `<meta name="description">` content
  - Primeiro `<h1>`
  - `<link rel="canonical" href="...">` — classificar como: `auto` (aponta para si mesma), `externo` (duplicata — alerta), `ausente` (risco)
  - Contagem de palavras visíveis (texto de `<p>`, `<li>`, `<h1>`–`<h6>`, sem scripts/styles)
  - Schema.org: `extruct.extract(html, base_url=url, syntaxes=["json-ld"])` — verificar tipo `AutoRepair` ou `LocalBusiness`
  - URL de origem (referrer) para detecção de links quebrados: registrar qual página linkou para cada URL

  > Envolver `extruct.extract()` em `try/except Exception` — ele lança exceções não documentadas em HTML com scripts inline corrompidos.

- Ao final, cruzar páginas com `status_http == 404` com suas URLs de origem e adicionar coluna `linkado_por` ao CSV.

- Salvar em `output/1_auditoria_tecnica_site.csv`.

---

#### 2.6 `src/gsc_auditor.py`

- Autenticar via variável de ambiente `GOOGLE_CREDENTIALS_JSON`. **Estratégia de leitura:** gravar o conteúdo da variável em arquivo temporário `credentials_temp.json` antes de autenticar, pois o JSON de Service Account contém o campo `private_key` com quebras de linha PEM que podem ser corrompidas ao passar por variáveis de ambiente em alguns shells.

  ```python
  import tempfile, os, json
  creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
  if creds_json:
      with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
          f.write(creds_json)
          creds_path = f.name
      credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=[...])
      os.unlink(creds_path)
  ```

  Ou, se o arquivo local `credentials.json` existir, usá-lo diretamente.

- Se credencial não existir: `logging.warning` amigável e retornar `None`.

- **Probe automático de propriedade:** tentar `"sc-domain:redefox.com.br"` primeiro; em caso de HTTP 403/404, tentar `"https://redefox.com.br/"`. Gravar o formato que funcionou em `output/gsc_config.txt`.

- Extrair últimos 90 dias com dimensões `["page", "query"]`. Salvar em `output/2_gsc_performance.csv`. Aplicar `normalize_url()` na coluna `page` antes de salvar.

---

#### 2.7 `src/serp_scanner.py`

**Estratégia: Divide and Conquer entre 4 provedores — custo R$0–2/mês**

**Estado de cotas persistido em `.cache/serp_quota.json`:**
```json
{
  "reset_month": "2026-11",
  "brave":       { "used": 42 },
  "bing":        { "used": 0 },
  "tavily":      { "used": 0 },
  "dataforseo":  { "used": 0 },
  "cooldowns":   { "brave": null, "bing": null }
}
```
No início de cada `run()`, carregar este arquivo. Se `reset_month` for diferente do mês atual, zerar todos os contadores (`used: 0`) e atualizar `reset_month`. Salvar após cada query bem-sucedida.

**Seleção de provedor (`_select_provider()`):**
Percorrer `SERP_PROVIDERS` em ordem de `priority`. Selecionar o primeiro que satisfaça:
1. `env_key` está definido como variável de ambiente (Secret configurado)
2. `used < monthly_quota`
3. Não está em cooldown (campo `cooldowns[name]` nulo ou timestamp passado)

Se nenhum provedor disponível: `logging.error` e retornar `None` para a query (não lançar exceção — pipeline continua).

**Cache de resultados em `.cache/cache_serp.json`:**
Pular buscas já cacheadas com menos de 7 dias. Salvar imediatamente após cada resultado bem-sucedido. Chave: `f"{slugify(servico)}_{slugify(cidade)}"`.

**Buscas em dois grupos:**

- **Grupo 1 — Serviços por cidade:** `"{Serviço} em {Cidade} {UF}"` para cada combinação unidade × serviço da mesma linha (~130 queries)
- **Grupo 2 — Medidas de pneus:** `"pneu {medida} {cidade}"` para as 5 primeiras `MEDIDAS_PNEUS_CHAVE` × top 5 cidades (Manaus, Porto Velho, Ariquemes, Ji-Paraná, Vilhena) = 25 queries extras

**Execução em lotes paralelos de 5 queries simultâneas:**
`concurrent.futures.ThreadPoolExecutor(max_workers=5)` com `time.sleep(1)` entre lotes. Total ~155 queries ÷ 5 = 31 lotes × ~2s = **~62 segundos** (vs 5+ minutos sequencial).

**Implementação dos 4 adaptadores:**

```python
def _search_brave(query: str, key: str) -> list[dict]:
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": 10, "country": "BR", "search_lang": "pt"},
        timeout=30
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["title"]}
            for r in resp.json().get("web", {}).get("results", [])]

def _search_bing(query: str, key: str) -> list[dict]:
    resp = requests.get(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": key},
        params={"q": query, "count": 10, "mkt": "pt-BR", "cc": "BR"},
        timeout=30
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["name"]}
            for r in resp.json().get("webPages", {}).get("value", [])]

def _search_tavily(query: str, key: str) -> list[dict]:
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": 10,
              "include_domains": [], "search_depth": "basic"},
        timeout=30
    )
    resp.raise_for_status()
    return [{"url": r["url"], "title": r["title"]}
            for r in resp.json().get("results", [])]

def _search_dataforseo(query: str, login_b64: str) -> list[dict]:
    import base64
    creds = base64.b64decode(login_b64).decode()
    login, password = creds.split(":", 1)
    resp = requests.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        auth=(login, password),
        json=[{"keyword": query, "location_name": "Brazil",
               "language_name": "Portuguese", "depth": 10}],
        timeout=30
    )
    resp.raise_for_status()
    items = resp.json()["tasks"][0]["result"][0].get("items", [])
    return [{"url": i["url"], "title": i["title"]}
            for i in items if i.get("type") == "organic"]
```

**Retry com tenacity (aplicado em cada adaptador individualmente):**
```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

@retry(wait=wait_exponential(multiplier=1, min=2, max=32),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(Exception))
def _fetch_with_provider(query, provider_name, key): ...
```

Em caso de HTTP 429 ou 503: marcar o provedor com cooldown de 1 hora em `serp_quota.json` e tentar o próximo provedor disponível (não contar como uso de cota).

Para cada busca: posição da Fox no Top 10 (ou `None`), 3 domínios concorrentes principais. Salvar em `output/3_serp_concorrencia_local.csv`.

**Calcular Share of Voice ao final de `run()`:**
```python
df = pd.read_csv("output/3_serp_concorrencia_local.csv")
total_queries = len(df)
fox_presente = df["posicao_fox"].notna().sum()
share_of_voice = round((fox_presente / total_queries) * 100, 1) if total_queries > 0 else 0.0
# Salvar em output/share_of_voice.json para o dashboard consumir
import json
with open("output/share_of_voice.json", "w", encoding="utf-8") as f:
    json.dump({
        "share_of_voice_pct": share_of_voice,
        "fox_presente_em": int(fox_presente),
        "total_queries_monitoradas": total_queries,
        "data": datetime.now().strftime("%Y-%m-%d")
    }, f, ensure_ascii=False, indent=2)
```

> **Share of Voice** = % das buscas locais monitoradas em que a Fox aparece no Top 10. Meta inicial: 30%. Acima de 60% indica liderança regional. É a métrica executiva mais importante do sistema — resume em um número o impacto total de todas as ações de SEO.

---

#### 2.8 `src/reviews_monitor.py` — Monitoramento de Avaliações Google

- Usar **Google Places API** (free tier: 200 req/dia — suficiente para 10 unidades).
  - Endpoint: `https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={nome}+{cidade}&inputtype=textquery&fields=place_id,rating,user_ratings_total&key={PLACES_API_KEY}`
  - Se `PLACES_API_KEY` não definido: `logging.warning` e retornar — módulo é opcional.

- Para cada unidade em `UNIDADES`:
  1. Buscar `place_id` via `findplacefromtext` usando `{unidade['nome']} {unidade['cidade']}`.
  2. Obter `rating` e `user_ratings_total` via `place/details`.
  3. Usar `time.sleep(0.2)` entre requisições para respeitar rate limit.

- Lógica de alerta:
  - `rating < 4.0` → `status = "ALERTA"` — unidade pode perder posição no Maps Pack
  - `4.0 <= rating < 4.5` → `status = "ATENÇÃO"`
  - `rating >= 4.5` → `status = "OK"`
  - Se a unidade não tiver avaliações novas há mais de 30 dias (comparando com execução anterior): `status = "ESTAGNADO"`

- Comparar com execução anterior lendo `output/7_reviews_monitor.csv` já existente. Adicionar coluna `delta_avaliacoes` (diferença de `user_ratings_total` desde a última execução).

- Salvar em `output/7_reviews_monitor.csv` com colunas: `unidade`, `cidade`, `uf`, `place_id`, `rating`, `total_avaliacoes`, `delta_avaliacoes`, `status`, `data_coleta`.

> **Por que isso importa para SEO local:** O Google Maps Pack prioriza negócios com rating ≥ 4.0 e volume crescente de avaliações. Uma unidade com 3.8 estrelas pode desaparecer do Maps Pack independente de ter schema perfeito. Este módulo detecta a queda antes que ela impacte o tráfego.

---

#### 2.8b `src/gap_analyzer.py`

- Carregar todos os CSVs com `normalize_url()` aplicado nas colunas de URL antes de qualquer merge. Normalizar protocolo (http→https), remover www, remover trailing slash.

- Gerar `output/4_plano_expansao_landing_pages.csv` com colunas: `Cidade`, `UF`, `Linha`, `Servico`, `Status_Atual`, `URL_Sugerida`, `Title_SEO`, `Meta_Description`.

  Templates com validação de tamanho:
  - **Title SEO** (máx. 60 chars): `"{Serviço} em {Cidade} {UF} | Rede Fox"` — se ultrapassar, truncar o nome do serviço antes do ` | Rede Fox`.
  - **Meta Description** (máx. 155 chars): `"Fox {Cidade}: {Serviço} com qualidade garantida. Atendimento para {linha}. Ligue {telefone}."` — se ultrapassar, truncar na última palavra completa e adicionar `"."`.

- Gerar `output/4_plano_expansao.xlsx` via `pandas.DataFrame.to_excel("output/4_plano_expansao.xlsx", index=False)` para download direto.

- **Gerar `output/urls_para_indexar.txt` automaticamente** com todas as `URL_Sugerida` onde `Status_Atual != "existe"`. Este arquivo alimenta o `indexing_pusher.py`. Sem essa geração automática, o módulo de indexação nunca teria URLs para processar.

- **Gerar FAQ Schema (`FAQPage`) para cada landing page sugerida.** Nota (2026): o Google deixou de exibir o FAQ como rich result ("People Also Ask") para sites comuns, então o bloco não gera mais essa caixa na SERP. Ainda assim o `FAQPage` segue valioso e deve ser gerado: ajuda os buscadores de IA (ChatGPT, Gemini, Perplexity) e a busca por voz a entender e citar o conteúdo, além de reforçar a clareza semântica da página. Adicionar ao JSON-LD de cada landing page:

  ```json
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "Quanto custa {Serviço} em {Cidade}?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "O preço de {Serviço} na Fox {Cidade} varia conforme o veículo. Ligue {telefone} para orçamento sem compromisso."
        }
      },
      {
        "@type": "Question",
        "name": "Quanto tempo leva {Serviço} na Fox {Cidade}?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "O serviço de {Serviço} na Fox {Cidade} leva em média 1 a 2 horas, dependendo do veículo. Atendemos de {horario}."
        }
      },
      {
        "@type": "Question",
        "name": "A Fox {Cidade} oferece garantia em {Serviço}?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Sim. Todos os serviços da Rede Fox têm garantia. Consulte nosso time em {telefone}."
        }
      }
    ]
  }
  ```

  Salvar os schemas FAQ em `output/5b_schemas_faqpage_sugeridos.json` (separado do AutoRepair para facilitar implementação pelo time de desenvolvimento).

  > **Implementação no site:** os dois schemas (`AutoRepair` + `FAQPage`) devem ser inseridos como dois blocos `<script type="application/ld+json">` separados na mesma página — o Google aceita múltiplos schemas na mesma URL.

- Gerar `output/5_schemas_jsonld_sugeridos.json` com schema `AutoRepair` **correto e completo** para cada unidade:

  ```json
  {
    "@context": "https://schema.org",
    "@type": "AutoRepair",
    "name": "Fox Manaus",
    "url": "https://redefox.com.br/unidades/manaus",
    "telephone": "(92) 3622-7777",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Av. Tarumã, 700, Praça 14 de Janeiro",
      "addressLocality": "Manaus",
      "addressRegion": "AM",
      "addressCountry": "BR"
    },
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": -3.1190,
      "longitude": -60.0217
    },
    "openingHours": "Mo-Fr 08:00-18:00, Sa 08:00-12:00",
    "paymentAccepted": "Dinheiro, Cartão de Crédito, Cartão de Débito, PIX",
    "priceRange": "$$",
    "hasOfferCatalog": {
      "@type": "OfferCatalog",
      "name": "Serviços Automotivos",
      "itemListElement": [
        { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Pneus e Geometria 3D" } }
      ]
    }
  }
  ```

  > **Remover** `servesCuisine` — é propriedade de `FoodEstablishment` (restaurantes). Em `AutoRepair` é ruído que o Google Search Console reporta como "propriedade inesperada" e reduz a qualidade do schema.

- Gerar `output/sitemap_sugerido.xml` com todas as URLs do plano de expansão em formato `<urlset>` padrão:
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
      <loc>https://redefox.com.br/servicos/pneus-geometria-3d-manaus</loc>
      <changefreq>monthly</changefreq>
      <priority>0.8</priority>
      <lastmod>YYYY-MM-DD</lastmod>
    </url>
  </urlset>
  ```

---

#### 2.9 `src/indexing_pusher.py`

- Se `output/urls_para_indexar.txt` não existir ou estiver vazio: `logging.info` e retornar. O arquivo é gerado automaticamente pelo `gap_analyzer`.

- **Mecanismo 1 — IndexNow (Bing/Yandex):** envio em lote para `https://api.indexnow.org/indexnow` com `INDEXNOW_KEY`. Sem restrição de tipo de schema. Retorna resultado imediato.

- **Mecanismo 2 — Google Indexing API:** somente para URLs com `tem_schema = True` no CSV de auditoria (tipos `JobPosting` ou `BroadcastEvent`). Autenticar com `GOOGLE_CREDENTIALS_JSON` via arquivo temporário (mesma estratégia do `gsc_auditor.py`).

- **Mecanismo 3 — Sitemap ping:** sempre ao final, independente do restante:
  `GET https://www.google.com/ping?sitemap=https://redefox.com.br/sitemap.xml`

---

#### 2.10 `src/core_web_vitals.py`

- Usar PageSpeed Insights API para as 10 URLs mais importantes (homepage + páginas de unidades se existirem no CSV de auditoria).

- URL base: `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile`
  Se `PSI_API_KEY` definido: adicionar `&key={PSI_API_KEY}` (aumenta rate limit de 25 para 400 req/dia).

- Usar `time.sleep(1)` entre requisições. Se receber HTTP 429: backoff de 60 segundos e retentativa única.

- Extrair: `LCP`, `CLS`, `INP` (ou `FID` se INP não disponível), `Performance Score` (0–100).

- Salvar em `output/6_core_web_vitals.csv`. Se a API falhar inteiramente: `logging.warning` e continuar.

---

#### 2.11 `src/dashboard_builder.py` — Painel Executivo para Diretoria

**Validação obrigatória antes de gerar:**
Para cada CSV de entrada, verificar que tem pelo menos 1 linha de dados. Se vazio, registrar o módulo como "indisponível" e renderizar um banner de alerta vermelho no dashboard: `"⚠ Dados de [módulo] indisponíveis nesta execução — exibindo última atualização de [data]."`.

**Serialização de dados:**
Todos os dados dos CSVs devem ser lidos em Python e serializados como JSON embutido no HTML via Jinja2. O arquivo `docs/index.html` deve funcionar como página estática offline sem nenhuma requisição de dados.

```python
# Correto — embutir dados como JSON
expansion_data = df.to_dict(orient="records")
# No template Jinja2:
# window.expansionData = {{ expansion_data | tojson }};
```

**Gráficos — usar `fig.to_json()` obrigatoriamente:**
```python
fig = go.Figure(...)
fig_json = fig.to_json()  # serializa apenas dados + layout, sem o plotly.js (3MB)
# No template: Plotly.newPlot('div-id', JSON.parse('{{ fig_json | safe }}').data, ...)
```
Nunca usar `fig.to_html(full_html=True)` — embute 3MB de JS por gráfico.

**Dependências CDN — ordem e versões exatas:**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css">
<script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
```

> **Versão crítica:** DataTables `1.13.8` (não 1.10.21). O plugin Buttons 2.4.2 requer DataTables 1.13+. Usar 1.10 com Buttons 2.4 causa erro JS silencioso — botões aparecem mas não funcionam.

**Design:** fundo `#0f172a`, cards `#1e293b`, acentos `#f97316` (laranja Fox) e `#3b82f6`, textos brancos/cinza-claro.

**Conteúdo obrigatório:**

1. **Cabeçalho:** "Inteligência de Busca & Expansão Web — Rede Fox" + data/hora da geração.

2. **5 Cards KPIs:** Total de Páginas Mapeadas, Taxa de Cobertura Local (%), Novas Landing Pages Recomendadas, Páginas sem Schema.org, e **Share of Voice (%)** lido de `output/share_of_voice.json` — exibir com gauge visual (verde ≥ 60%, laranja 30–60%, vermelho < 30%).

3. **Gráfico 1 — Barras Empilhadas:** Cobertura de Serviços por Cidade (Top 10 vs. Faltantes).

4. **Gráfico 2 — Rosca:** Saúde Técnica On-Page (com Schema.org vs. sem).

5. **Gráfico 3 — Barras Horizontais:** Top 10 Concorrentes Locais nas buscas onde a Fox está ausente.

6. **Gráfico 4 — Linha Temporal:** Evolução semanal de KPIs. **Exibir apenas as últimas 52 semanas** (1 ano) para manter o gráfico legível. Ler de `output/historico_evolucao.csv` e filtrar `df.tail(52)`.

7. **Gráfico 5 — Barras com referências:** Core Web Vitals (LCP, CLS, INP) com linhas de threshold: LCP ≤ 2.5s verde, 2.5–4s laranja, > 4s vermelho.

8. **Gráfico 6 — Share of Voice Histórico:** linha temporal do `share_of_voice_pct` lida de `output/historico_evolucao.csv`. Exibir meta de 60% como linha tracejada horizontal de referência. Limitar a `df.tail(52)`.

9. **Gráfico 7 — Reviews por Unidade:** barras horizontais com `rating` de cada unidade (de `output/7_reviews_monitor.csv`). Colorir: verde ≥ 4.5, laranja 4.0–4.5, vermelho < 4.0. Exibir alerta visual para unidades com `status == "ALERTA"` ou `"ESTAGNADO"`. Se o CSV não existir (módulo opcional), exibir banner informativo: `"ℹ Reviews Monitor desativado — configure PLACES_API_KEY para habilitar."`.

10. **Tabela DataTables:** Plano de expansão com busca, filtro por cidade, e botões "Exportar CSV" e "Exportar Excel". Dados embutidos como `window.expansionData`.

**Histórico:** A cada execução, registrar linha em `output/historico_evolucao.csv`: `data`, `paginas_mapeadas`, `cobertura_local_pct`, `lps_recomendadas`, `paginas_sem_schema`, `score_medio_performance`, `share_of_voice_pct` (de `output/share_of_voice.json`), `media_rating_unidades` (de `output/7_reviews_monitor.csv`, média do campo `rating`).

---

#### 2.12 `main.py`

```python
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    # Backup dos dados anteriores antes de sobrescrever
    _backup_outputs()

    etapas = [
        ("crawler_site",    crawler_site.run),
        ("gsc_auditor",     gsc_auditor.run),
        ("serp_scanner",    serp_scanner.run),   # calcula Share of Voice ao final
        ("core_web_vitals", core_web_vitals.run),
        ("gap_analyzer",    gap_analyzer.run),   # gera FAQ schemas
        ("reviews_monitor", reviews_monitor.run),  # opcional — requer PLACES_API_KEY
        ("indexing_pusher", indexing_pusher.run),
        ("dashboard_builder", dashboard_builder.run),
    ]

    resultados = {}
    for nome, fn in etapas:
        t0 = datetime.now()
        try:
            fn()
            resultados[nome] = ("✅ OK", datetime.now() - t0)
        except Exception as e:
            logging.error(f"{nome} falhou: {e}", exc_info=True)
            resultados[nome] = ("❌ Falhou", datetime.now() - t0)

    _gerar_relatorio(resultados)

def _backup_outputs():
    """Copia CSVs existentes para output/backup/YYYY-MM-DD/ antes de sobrescrever."""
    import shutil
    from pathlib import Path
    backup_dir = Path("output/backup") / datetime.now().strftime("%Y-%m-%d")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for csv in Path("output").glob("*.csv"):
        shutil.copy2(csv, backup_dir / csv.name)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Pipeline interrompido pelo usuário.")
        sys.exit(0)
```

**Timeout por módulo:** usar `multiprocessing.Process` (não `ThreadPoolExecutor`) para módulos de longa duração — processos são verdadeiramente encerráveis, threads não:

```python
import multiprocessing

def _run_with_timeout(fn, timeout_seconds, nome):
    p = multiprocessing.Process(target=fn)
    p.start()
    p.join(timeout=timeout_seconds)
    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError(f"{nome} excedeu {timeout_seconds}s e foi encerrado.")
```

Usar `timeout=600` para o crawler e `timeout=1200` para o SERP scanner.

**Relatório executivo** `output/RELATORIO_EXECUTIVO.md` — template mínimo sempre gerado mesmo com falhas parciais:

```markdown
# Relatório Executivo — Rede Fox SEO Engine
**Gerado em:** {data_hora}

## Resumo de KPIs
- Páginas mapeadas: {n}
- Cobertura local: {pct}%
- Landing pages recomendadas: {n}
- Páginas sem Schema.org: {n}

## Status dos Módulos
| Módulo | Status | Duração |
|---|---|---|
| crawler_site | ✅ OK | 45s |
...

## Top 5 Oportunidades de Expansão
{tabela dos 5 primeiros itens do plano de expansão}
```

---

#### 2.13 `.github/workflows/seo_audit_pipeline.yml`

```yaml
name: Fox SEO Engine — Weekly Audit

on:
  schedule:
    - cron: '0 6 * * 1'   # Segunda-feira 6h UTC = 3h BRT; termina ~4h BRT, antes do expediente
  workflow_dispatch:

permissions:
  contents: write

jobs:
  audit:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # clone completo — evita "rejected: remote contains work you do not have"

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Restore SERP cache
        uses: actions/cache@v4
        with:
          path: .cache/
          key: serp-cache-${{ steps.date.outputs.week }}
          restore-keys: serp-cache-

      - name: Get current week number
        id: date
        run: echo "week=$(date +'%Y-W%V')" >> $GITHUB_OUTPUT

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Write Google credentials to file
        if: env.GOOGLE_CREDENTIALS_JSON != ''
        run: echo '${{ secrets.GOOGLE_CREDENTIALS_JSON }}' > credentials.json
        env:
          GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}

      - name: Run SEO pipeline
        env:
          GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}
          # SERP — rotação entre 4 provedores (R$0–2/mês total)
          BRAVE_SEARCH_KEY:   ${{ secrets.BRAVE_SEARCH_KEY }}
          BING_SEARCH_KEY:    ${{ secrets.BING_SEARCH_KEY }}
          TAVILY_API_KEY:     ${{ secrets.TAVILY_API_KEY }}
          DATAFORSEO_LOGIN:   ${{ secrets.DATAFORSEO_LOGIN }}
          # Outros
          INDEXNOW_KEY:   ${{ secrets.INDEXNOW_KEY }}
          PSI_API_KEY:    ${{ secrets.PSI_API_KEY }}
          PLACES_API_KEY: ${{ secrets.PLACES_API_KEY }}
        run: python main.py

      - name: Clean up credentials
        if: always()
        run: rm -f credentials.json

      - name: Check for changes
        id: check_changes
        run: |
          git add output/ docs/
          git diff --staged --quiet && echo "changed=false" >> $GITHUB_OUTPUT || echo "changed=true" >> $GITHUB_OUTPUT

      - name: Commit and push results
        if: steps.check_changes.outputs.changed == 'true'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git commit -m "chore: atualização automática do relatório SEO $(date +'%Y-%m-%d')"
          git push

      - name: Upload outputs as artifact (debug)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: seo-outputs-${{ github.run_id }}
          path: output/
          retention-days: 7

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: 1,
              body: `❌ **Fox SEO Engine falhou** em ${new Date().toISOString()}. [Ver logs](${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId})`
            });
```

> **Notas obrigatórias:**
> - `fetch-depth: 0` evita erro de push por histórico incompleto.
> - `actions/cache@v4` persiste o `.cache/cache_serp.json` entre execuções sem poluir o git com diffs de cache.
> - `credentials.json` é escrito e removido dentro do job — nunca commitado.
> - Email `41898282+github-actions[bot]@users.noreply.github.com` é o email padrão oficial do GitHub Actions bot.
> - `upload-artifact` com `if: always()` preserva os CSVs para debug mesmo em falhas.
> - Cron `0 6 * * 1` = 6h UTC = 3h BRT. Pipeline termina ~4h BRT. Dashboard pronto antes do expediente.

---

#### 2.14 `.gitignore`

```
venv/
.venv/
__pycache__/
*.pyc
.env
credentials.json
credentials_temp.json
.cache/
output/backup/
```

> `.cache/` é gerenciado pelo `actions/cache@v4`, não pelo git. `output/backup/` cresce indefinidamente e não deve ser versionado.

---

#### 2.15 `README.md`

Incluir:
1. Descrição e diagrama de arquitetura (fluxo dos 7 módulos)
2. Badge de status do workflow: `![SEO Audit](https://github.com/{owner}/{repo}/actions/workflows/seo_audit_pipeline.yml/badge.svg)`
3. **Configuração de Secrets** (Settings → Secrets → Actions):
   - `GOOGLE_CREDENTIALS_JSON` — JSON completo da Service Account
   - `SERPAPI_KEY` — opcional, fallback para DDG
   - `INDEXNOW_KEY` — de `https://www.indexnow.org/`
   - `PSI_API_KEY` — opcional, aumenta rate limit do PageSpeed
4. **Ativar GitHub Pages:** Settings → Pages → branch `main` → folder `/docs`
5. **Execução local:** `cp .env.example .env && pip install -r requirements.txt && python main.py`
6. Tabela de outputs com descrição de cada arquivo em `output/`

---

### 3. Requisitos Transversais Obrigatórios

**Todos os módulos:**
- `logging.getLogger(__name__)` — nunca `print()`
- `timeout=30` em todas as requisições `requests.get()`/`requests.post()`; usar `httpx.Timeout(connect=5.0, read=10.0)` no crawler
- `encoding="utf-8"` ao abrir/salvar CSV e JSON
- Importar `slugify` e `normalize_url` de `config.matriz_negocio` — nunca reimplementar

**Módulos com escrita de arquivo:**
- Validar que o DataFrame não está vazio antes de salvar. Se vazio, logar warning e não sobrescrever o arquivo anterior (manter o último dado válido).

---

### 4. Checklist de Revisão Final

Antes de considerar o projeto pronto, verificar **cada item**:

**Estrutura:**
- [ ] `config/__init__.py` existe (arquivo vazio)
- [ ] `.env.example` existe com todos os 4 Secrets documentados
- [ ] `.cache/.gitkeep` existe e `.cache/` está no `.gitignore`
- [ ] `output/backup/` está no `.gitignore`

**Código:**
- [ ] `main.py` tem guard `if __name__ == "__main__": main()`
- [ ] `main.py` tem `_backup_outputs()` antes do pipeline
- [ ] `main.py` usa `multiprocessing.Process` para timeouts (não ThreadPoolExecutor)
- [ ] `extruct.extract()` envolvido em `try/except Exception`
- [ ] `DDGS().text()` envolto em `list()` e checa lista vazia (não apenas exceções)
- [ ] `gap_analyzer.run()` gera `output/urls_para_indexar.txt` automaticamente
- [ ] Todos os merges de DataFrame usam `normalize_url()` antes do join
- [ ] `servesCuisine` **ausente** dos schemas JSON-LD (propriedade de restaurante)
- [ ] `openingHours` e `hasOfferCatalog` **presentes** nos schemas JSON-LD
- [ ] `slugify` e `normalize_url` importados de `config.matriz_negocio` em todos os módulos

**Dashboard:**
- [ ] Dados embutidos como JSON no HTML (não leitura de CSV no browser)
- [ ] `fig.to_json()` usado — nunca `fig.to_html(full_html=True)`
- [ ] DataTables versão `1.13.8` (não 1.10.21)
- [ ] jQuery carregado antes de todos os plugins DataTables
- [ ] Banner de alerta quando CSV de entrada está vazio
- [ ] Gráfico de linha temporal limita a `df.tail(52)`

**Workflow:**
- [ ] `fetch-depth: 0` no checkout
- [ ] `actions/cache@v4` para o `.cache/` (cache SERP + estado de cotas)
- [ ] `credentials.json` removido com `if: always()` após o job
- [ ] Git user.email = `41898282+github-actions[bot]@users.noreply.github.com`
- [ ] `upload-artifact` com `if: always()` para debug
- [ ] `notify on failure` step presente
- [ ] Cron = `0 6 * * 1` (não `0 8 * * 1`)
- [ ] 4 Secrets SERP configurados: `BRAVE_SEARCH_KEY`, `BING_SEARCH_KEY`, `TAVILY_API_KEY`, `DATAFORSEO_LOGIN`

**SERP — rotação de provedores:**
- [ ] `SERP_PROVIDERS` definido em `config/matriz_negocio.py` com os 4 provedores e suas cotas
- [ ] `.cache/serp_quota.json` inicializado com `reset_month`, contadores `used` e campo `cooldowns`
- [ ] `_select_provider()` percorre provedores por prioridade verificando: Secret definido + cota disponível + sem cooldown ativo
- [ ] Reset automático de contadores quando `reset_month != mês atual`
- [ ] Cooldown de 1h ao receber HTTP 429/503 (sem consumir cota)
- [ ] DataForSEO usado exclusivamente como overflow (priority 4) — nunca antes dos gratuitos esgotarem
- [ ] 4 adaptadores implementados: `_search_brave`, `_search_bing`, `_search_tavily`, `_search_dataforseo`
- [ ] Grupo 2 de busca (medidas de pneus) implementado: top 5 medidas × top 5 cidades

**SEO:**
- [ ] Crawler verifica `robots.txt` antes de crawlar
- [ ] Crawler extrai `rel="canonical"` e classifica
- [ ] Crawler rastreia referrers para detectar links quebrados
- [ ] `gap_analyzer` gera `output/sitemap_sugerido.xml`
- [ ] `gap_analyzer` gera `output/5b_schemas_faqpage_sugeridos.json` com 3 perguntas por landing page
- [ ] `serp_scanner` calcula Share of Voice e salva em `output/share_of_voice.json`
- [ ] `serp_scanner` inclui loop de medidas de pneus (top 5 × top 5 cidades)
- [ ] `reviews_monitor` retorna graciosamente se `PLACES_API_KEY` não definido (não bloqueia pipeline)
- [ ] `reviews_monitor` salva em `output/7_reviews_monitor.csv` com colunas `rating`, `status`, `delta_avaliacoes`
- [ ] `slug_cidade` único para Porto Velho (3 variantes) e Vilhena (2 variantes)
- [ ] Campo `horario` presente em todas as unidades da `UNIDADES` list

**Novas funcionalidades e-commerce:**
- [ ] FAQ Schema (`FAQPage`) gerado para cada landing page sugerida com 3 perguntas/respostas
- [ ] Share of Voice (%) exibido no dashboard como 5º KPI card com gauge colorido
- [ ] Gráfico 6 (Share of Voice histórico) com linha de meta em 60%
- [ ] Gráfico 7 (Reviews por unidade) com cores por threshold e alerta para status ALERTA/ESTAGNADO
- [ ] `historico_evolucao.csv` inclui colunas `share_of_voice_pct` e `media_rating_unidades`
- [ ] `PLACES_API_KEY` documentado no `.env.example` como opcional
- [ ] `PLACES_API_KEY` como Secret no workflow YAML
- [ ] `main.py` inclui `reviews_monitor` na lista de etapas

Crie todos os arquivos agora com código funcional completo e revise importações e sintaxe para garantir que o projeto rode de primeira sem erros.
