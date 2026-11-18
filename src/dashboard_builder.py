import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template

logger = logging.getLogger(__name__)

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inteligência SEO — Rede Fox</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css">
<script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --muted: #94a3b8;
    --border: #334155; --input-bg: #0f172a; --hover: #334155;
    --alert-bg: #7f1d1d; --alert-border: #ef4444;
  }
  :root[data-theme="light"] {
    --bg: #f1f5f9; --card: #ffffff; --text: #0f172a; --muted: #64748b;
    --border: #e2e8f0; --input-bg: #ffffff; --hover: #f8fafc;
    --alert-bg: #fee2e2; --alert-border: #ef4444;
  }
  body { background:var(--bg); color:var(--text); font-family:sans-serif; transition:background .2s,color .2s; }
  .card { background:var(--card); border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,.12); }
  .accent { color:#f97316; }
  .alert-banner { background:var(--alert-bg); border:1px solid var(--alert-border); border-radius:8px; padding:12px 16px; margin-bottom:12px; }
  .kpi-gauge { font-size:12px; padding:2px 8px; border-radius:9999px; font-weight:600; display:inline-block; }
  .gauge-green { background:#166534; color:#86efac; }
  .gauge-orange { background:#78350f; color:#fcd34d; }
  .gauge-red { background:#7f1d1d; color:#fca5a5; }
  :root[data-theme="light"] .gauge-green { background:#dcfce7; color:#166534; }
  :root[data-theme="light"] .gauge-orange { background:#ffedd5; color:#9a3412; }
  :root[data-theme="light"] .gauge-red { background:#fee2e2; color:#991b1b; }
  /* DataTables */
  table.dataTable thead th { background:var(--bg) !important; color:var(--muted) !important; border-bottom:1px solid var(--border) !important; }
  table.dataTable tbody tr { background:var(--card) !important; }
  table.dataTable tbody tr:hover { background:var(--hover) !important; }
  table.dataTable tbody td { color:var(--text) !important; border-color:var(--border) !important; }
  .dataTables_wrapper .dataTables_filter input,
  .dataTables_wrapper select { background:var(--input-bg); color:var(--text); border:1px solid var(--border); border-radius:4px; padding:4px 8px; }
  .dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate { color:var(--muted); }
  .dataTables_wrapper .dataTables_paginate .paginate_button { color:var(--muted) !important; }
  .dataTables_wrapper .dataTables_paginate .paginate_button.current { background:#f97316 !important; color:#fff !important; border-radius:4px; }
  .dt-buttons .dt-button { background:var(--card) !important; color:var(--text) !important; border:1px solid var(--border) !important; border-radius:4px; padding:4px 12px; margin-right:4px; }
  /* Toggle button */
  #theme-toggle { cursor:pointer; border:1px solid var(--border); border-radius:8px; padding:6px 12px; background:var(--card); color:var(--text); font-size:13px; display:flex; align-items:center; gap:6px; transition:background .2s; }
  #theme-toggle:hover { background:var(--hover); }
</style>
</head>
<body class="p-6">

<div class="mb-8 flex items-start justify-between flex-wrap gap-3">
  <div>
    <h1 class="text-2xl font-bold accent mb-1">Inteligência de Busca &amp; Expansão Web — Rede Fox</h1>
    <p class="text-sm" style="color:var(--muted)">Gerado em {{ gerado_em }} &nbsp;·&nbsp; Atualizado toda segunda-feira às 4h BRT</p>
  </div>
  <button id="theme-toggle" onclick="toggleTheme()">
    <span id="theme-icon">🌙</span>
    <span id="theme-label">Tema Claro</span>
  </button>
</div>

{% for banner in alertas %}
<div class="alert-banner mb-4">⚠ {{ banner }}</div>
{% endfor %}

<!-- KPIs -->
<div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
  <div class="card p-5 text-center">
    <div class="text-3xl font-bold accent">{{ kpis.paginas_mapeadas }}</div>
    <div class="text-xs text-slate-400 mt-1">Páginas Mapeadas</div>
  </div>
  <div class="card p-5 text-center">
    <div class="text-3xl font-bold text-blue-400">{{ kpis.cobertura_pct }}%</div>
    <div class="text-xs text-slate-400 mt-1">Cobertura Local</div>
  </div>
  <div class="card p-5 text-center">
    <div class="text-3xl font-bold text-green-400">{{ kpis.lps_recomendadas }}</div>
    <div class="text-xs text-slate-400 mt-1">Landing Pages a Criar</div>
  </div>
  <div class="card p-5 text-center">
    <div class="text-3xl font-bold text-yellow-400">{{ kpis.sem_schema }}</div>
    <div class="text-xs text-slate-400 mt-1">Páginas sem Schema</div>
  </div>
  <div class="card p-5 text-center">
    <div class="text-3xl font-bold {{ 'text-green-400' if kpis.share_of_voice >= 60 else ('text-yellow-400' if kpis.share_of_voice >= 30 else 'text-red-400') }}">{{ kpis.share_of_voice }}%</div>
    <div class="text-xs text-slate-400 mt-1">Share of Voice</div>
    <span class="kpi-gauge {{ 'gauge-green' if kpis.share_of_voice >= 60 else ('gauge-orange' if kpis.share_of_voice >= 30 else 'gauge-red') }}">
      {{ 'Líder' if kpis.share_of_voice >= 60 else ('Crescendo' if kpis.share_of_voice >= 30 else 'Crítico') }}
    </span>
  </div>
</div>

<!-- Gráficos linha 1 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Cobertura de Serviços por Cidade</h3>
    <div id="chart-cobertura"></div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Saúde Técnica On-Page</h3>
    <div id="chart-saude"></div>
  </div>
</div>

<!-- Gráficos linha 2 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Top 10 Concorrentes Locais</h3>
    <div id="chart-concorrentes"></div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Evolução Semanal de KPIs</h3>
    <div id="chart-historico"></div>
  </div>
</div>

<!-- Gráficos linha 3 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Core Web Vitals (Mobile)</h3>
    <div id="chart-vitals"></div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold text-slate-300 mb-3">Share of Voice — Evolução</h3>
    <div id="chart-sov"></div>
  </div>
</div>

<!-- Reviews -->
<div class="card p-4 mb-6">
  <h3 class="text-sm font-semibold text-slate-300 mb-3">Avaliações Google por Unidade</h3>
  {% if reviews_disponivel %}
  <div id="chart-reviews"></div>
  {% else %}
  <p class="text-slate-400 text-sm">ℹ Reviews Monitor desativado — configure PLACES_API_KEY para habilitar.</p>
  {% endif %}
</div>

<!-- Tabela -->
<div class="card p-6 mb-6">
  <h3 class="text-sm font-semibold text-slate-300 mb-4">Plano de Expansão — Landing Pages</h3>
  <table id="tabela-expansao" class="display w-full text-sm">
    <thead>
      <tr>
        <th>Cidade</th><th>UF</th><th>Serviço</th><th>Status</th>
        <th>URL Sugerida</th><th>Title SEO</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</div>

<script>
const CHARTS = {{ charts_json | safe }};
const REVIEWS_DISPONIVEL = {{ 'true' if reviews_disponivel else 'false' }};

window.expansionData = {{ expansion_data | tojson }};

// Renderizar gráficos
const cfg = { responsive: true, displayModeBar: false };
const dark = { paper_bgcolor: '#1e293b', plot_bgcolor: '#1e293b',
               font: { color: '#e2e8f0', size: 11 } };

function renderChart(divId, figJson) {
  if (!figJson) return;
  try {
    const fig = JSON.parse(figJson);
    fig.layout = { ...fig.layout, ...dark };
    Plotly.newPlot(divId, fig.data, fig.layout, cfg);
  } catch(e) { console.warn('Chart error', divId, e); }
}

renderChart('chart-cobertura', CHARTS.cobertura);
renderChart('chart-saude', CHARTS.saude);
renderChart('chart-concorrentes', CHARTS.concorrentes);
renderChart('chart-historico', CHARTS.historico);
renderChart('chart-vitals', CHARTS.vitals);
renderChart('chart-sov', CHARTS.sov);
if (REVIEWS_DISPONIVEL) renderChart('chart-reviews', CHARTS.reviews);

// DataTable
$(document).ready(function() {
  const table = $('#tabela-expansao').DataTable({
    data: window.expansionData,
    columns: [
      { data: 'Cidade' }, { data: 'UF' }, { data: 'Servico' },
      { data: 'Status_Atual', render: d => d === 'existe'
        ? '<span style="color:#86efac">✓ Existe</span>'
        : '<span style="color:#fca5a5">✗ Ausente</span>' },
      { data: 'URL_Sugerida', render: d => `<a href="${d}" target="_blank" style="color:#60a5fa;word-break:break-all">${d}</a>` },
      { data: 'Title_SEO' },
    ],
    dom: 'Bfrtip',
    buttons: [
      { extend: 'csvHtml5', text: 'Exportar CSV', className: 'dt-button' },
      { extend: 'excelHtml5', text: 'Exportar Excel', className: 'dt-button' },
    ],
    pageLength: 25,
    language: {
      search: 'Buscar:', paginate: { previous: '‹', next: '›' },
      info: 'Mostrando _START_–_END_ de _TOTAL_ registros',
      lengthMenu: 'Mostrar _MENU_ por página',
    },
  });

  // Filtro por cidade
  $('#filtro-cidade').on('change', function() {
    table.column(0).search(this.value).draw();
  });
});

// ── Tema claro/escuro ────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const isLight = theme === 'light';
  document.getElementById('theme-icon').textContent = isLight ? '🌙' : '☀️';
  document.getElementById('theme-label').textContent = isLight ? 'Tema Escuro' : 'Tema Claro';

  // Re-render Plotly charts com cores do tema atual
  const bg = isLight ? '#ffffff' : '#1e293b';
  const paperBg = isLight ? '#ffffff' : '#1e293b';
  const fontColor = isLight ? '#0f172a' : '#e2e8f0';
  const plotUpdate = { paper_bgcolor: paperBg, plot_bgcolor: bg, font: { color: fontColor } };
  ['chart-cobertura','chart-saude','chart-concorrentes','chart-historico',
   'chart-vitals','chart-sov','chart-reviews'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el._fullLayout) Plotly.relayout(id, plotUpdate);
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('fox-seo-theme', next); } catch(e) {}
}

// Inicializar com preferência salva ou padrão do sistema
(function() {
  let saved;
  try { saved = localStorage.getItem('fox-seo-theme'); } catch(e) {}
  const pref = saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  applyTheme(pref);
})();
</script>
</body>
</html>"""


def _safe_load_csv(path: str) -> pd.DataFrame | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        df = pd.read_csv(p, encoding="utf-8")
        return df if not df.empty else None
    except Exception:
        return None


def _load_sov() -> float:
    p = Path("output/share_of_voice.json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("share_of_voice_pct", 0.0)
        except Exception:
            pass
    return 0.0


def _chart_cobertura(df_expansion: pd.DataFrame | None) -> str | None:
    if df_expansion is None:
        return None
    summary = df_expansion.groupby(["Cidade", "Status_Atual"]).size().unstack(fill_value=0)
    existe = summary.get("existe", pd.Series(dtype=int))
    ausente = summary.get("ausente", pd.Series(dtype=int))
    fig = go.Figure([
        go.Bar(name="Existe", x=summary.index.tolist(), y=existe.tolist(), marker_color="#22c55e"),
        go.Bar(name="Ausente", x=summary.index.tolist(), y=ausente.tolist(), marker_color="#f97316"),
    ])
    fig.update_layout(barmode="stack", height=320, margin=dict(t=20, b=40, l=20, r=20))
    return fig.to_json()


def _chart_saude(df_audit: pd.DataFrame | None) -> str | None:
    if df_audit is None:
        return None
    com = df_audit["tem_schema"].sum() if "tem_schema" in df_audit.columns else 0
    sem = len(df_audit) - com
    fig = go.Figure(go.Pie(
        labels=["Com Schema.org", "Sem Schema.org"],
        values=[com, sem],
        marker_colors=["#3b82f6", "#f97316"],
        hole=0.5,
    ))
    fig.update_layout(height=320, margin=dict(t=20, b=20, l=20, r=20))
    return fig.to_json()


def _chart_concorrentes(df_serp: pd.DataFrame | None) -> str | None:
    if df_serp is None:
        return None
    df_sem_fox = df_serp[df_serp["posicao_fox"].isna()]
    conc_counts: dict[str, int] = {}
    for col in ["concorrente_1", "concorrente_2", "concorrente_3"]:
        if col in df_sem_fox.columns:
            for v in df_sem_fox[col].dropna():
                conc_counts[v] = conc_counts.get(v, 0) + 1
    if not conc_counts:
        return None
    top10 = sorted(conc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    labels, values = zip(*top10)
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker_color="#3b82f6",
    ))
    fig.update_layout(height=360, margin=dict(t=20, b=20, l=160, r=20),
                      yaxis=dict(autorange="reversed"))
    return fig.to_json()


def _chart_historico(df_hist: pd.DataFrame | None) -> str | None:
    if df_hist is None:
        return None
    df = df_hist.tail(52)
    traces = []
    colors = {"cobertura_local_pct": "#3b82f6", "lps_recomendadas": "#f97316",
              "paginas_mapeadas": "#22c55e"}
    for col, color in colors.items():
        if col in df.columns:
            traces.append(go.Scatter(x=df["data"].tolist(), y=df[col].tolist(),
                                     mode="lines+markers", name=col.replace("_", " ").title(),
                                     line=dict(color=color)))
    if not traces:
        return None
    fig = go.Figure(traces)
    fig.update_layout(height=320, margin=dict(t=20, b=40, l=20, r=20))
    return fig.to_json()


def _chart_vitals(df_vitals: pd.DataFrame | None) -> str | None:
    if df_vitals is None:
        return None
    df = df_vitals.head(10)
    fig = go.Figure()
    if "lcp_s" in df.columns:
        colors = ["#22c55e" if v <= 2.5 else ("#f97316" if v <= 4.0 else "#ef4444")
                  for v in df["lcp_s"].fillna(0)]
        fig.add_trace(go.Bar(name="LCP (s)", x=df["url"].str[-40:].tolist(),
                             y=df["lcp_s"].tolist(), marker_color=colors))
    fig.add_hline(y=2.5, line_dash="dot", line_color="#22c55e", annotation_text="Meta LCP 2.5s")
    fig.add_hline(y=4.0, line_dash="dot", line_color="#ef4444", annotation_text="Crítico 4s")
    fig.update_layout(height=320, margin=dict(t=20, b=80, l=20, r=20),
                      xaxis=dict(tickangle=-30))
    return fig.to_json()


def _chart_sov(df_hist: pd.DataFrame | None, sov_atual: float) -> str | None:
    fig = go.Figure()
    if df_hist is not None and "share_of_voice_pct" in df_hist.columns:
        df = df_hist.tail(52)
        fig.add_trace(go.Scatter(
            x=df["data"].tolist(), y=df["share_of_voice_pct"].tolist(),
            mode="lines+markers", name="Share of Voice",
            line=dict(color="#f97316"),
        ))
    fig.add_hline(y=60, line_dash="dash", line_color="#22c55e",
                  annotation_text="Meta 60%")
    fig.update_layout(height=320, margin=dict(t=20, b=40, l=20, r=20),
                      yaxis=dict(range=[0, 100]))
    return fig.to_json()


def _chart_reviews(df_reviews: pd.DataFrame | None) -> str | None:
    if df_reviews is None:
        return None
    colors = []
    for _, row in df_reviews.iterrows():
        r = row.get("rating") or 0
        if r >= 4.5:
            colors.append("#22c55e")
        elif r >= 4.0:
            colors.append("#f97316")
        else:
            colors.append("#ef4444")
    fig = go.Figure(go.Bar(
        x=df_reviews["rating"].fillna(0).tolist(),
        y=df_reviews["unidade"].tolist(),
        orientation="h",
        marker_color=colors,
        text=df_reviews["status"].tolist(),
        textposition="outside",
    ))
    fig.add_vline(x=4.0, line_dash="dot", line_color="#f97316",
                  annotation_text="Mínimo 4.0")
    fig.update_layout(height=360, margin=dict(t=20, b=20, l=200, r=60),
                      xaxis=dict(range=[0, 5]))
    return fig.to_json()


def _update_historico(kpis: dict):
    path = Path("output/historico_evolucao.csv")
    row = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "paginas_mapeadas": kpis["paginas_mapeadas"],
        "cobertura_local_pct": kpis["cobertura_pct"],
        "lps_recomendadas": kpis["lps_recomendadas"],
        "paginas_sem_schema": kpis["sem_schema"],
        "score_medio_performance": kpis.get("score_medio", 0),
        "share_of_voice_pct": kpis["share_of_voice"],
        "media_rating_unidades": kpis.get("media_rating", 0),
    }
    if path.exists():
        df = pd.read_csv(path, encoding="utf-8")
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(path, index=False, encoding="utf-8")


def run():
    logger.info("Iniciando Dashboard Builder...")

    df_audit = _safe_load_csv("output/1_auditoria_tecnica_site.csv")
    df_gsc = _safe_load_csv("output/2_gsc_performance.csv")
    df_serp = _safe_load_csv("output/3_serp_concorrencia_local.csv")
    df_expansion = _safe_load_csv("output/4_plano_expansao_landing_pages.csv")
    df_vitals = _safe_load_csv("output/6_core_web_vitals.csv")
    df_reviews = _safe_load_csv("output/7_reviews_monitor.csv")
    df_hist = _safe_load_csv("output/historico_evolucao.csv")

    alertas = []
    modulos = {
        "Auditoria Técnica": df_audit,
        "GSC Performance": df_gsc,
        "SERP Concorrência": df_serp,
        "Plano de Expansão": df_expansion,
    }
    for nome, df in modulos.items():
        if df is None:
            alertas.append(f"Dados de {nome} indisponíveis nesta execução.")

    sov = _load_sov()

    # KPIs
    paginas = len(df_audit) if df_audit is not None else 0
    sem_schema = int(df_audit["tem_schema"].eq(False).sum()) if df_audit is not None and "tem_schema" in df_audit.columns else 0
    lps = int(df_expansion[df_expansion["Status_Atual"] != "existe"].shape[0]) if df_expansion is not None else 0
    total = int(df_expansion.shape[0]) if df_expansion is not None else 1
    existe_count = int(df_expansion[df_expansion["Status_Atual"] == "existe"].shape[0]) if df_expansion is not None else 0
    cobertura = round(existe_count / total * 100, 1) if total else 0.0
    score_medio = round(df_vitals["performance_score"].mean(), 1) if df_vitals is not None and "performance_score" in df_vitals.columns else 0
    media_rating = round(df_reviews["rating"].mean(), 2) if df_reviews is not None and "rating" in df_reviews.columns else 0

    kpis = {
        "paginas_mapeadas": paginas,
        "cobertura_pct": cobertura,
        "lps_recomendadas": lps,
        "sem_schema": sem_schema,
        "share_of_voice": sov,
        "score_medio": score_medio,
        "media_rating": media_rating,
    }

    _update_historico(kpis)
    df_hist = _safe_load_csv("output/historico_evolucao.csv")

    charts = {
        "cobertura": _chart_cobertura(df_expansion),
        "saude": _chart_saude(df_audit),
        "concorrentes": _chart_concorrentes(df_serp),
        "historico": _chart_historico(df_hist),
        "vitals": _chart_vitals(df_vitals),
        "sov": _chart_sov(df_hist, sov),
        "reviews": _chart_reviews(df_reviews),
    }

    expansion_data = df_expansion.to_dict(orient="records") if df_expansion is not None else []

    template = Template(TEMPLATE)
    html = template.render(
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
        alertas=alertas,
        kpis=kpis,
        charts_json=json.dumps(charts, ensure_ascii=False),
        expansion_data=expansion_data,
        reviews_disponivel=df_reviews is not None,
    )

    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(html, encoding="utf-8")
    logger.info("Dashboard gerado em docs/index.html")
