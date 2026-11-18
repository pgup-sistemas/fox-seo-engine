import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template

logger = logging.getLogger(__name__)

TEMPLATE = """<!DOCTYPE html>
{% macro empty_state(title, hint) %}
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:36px 24px;text-align:center;min-height:180px;gap:10px">
  <svg style="width:32px;height:32px;color:var(--border)" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6"/></svg>
  <p style="font-size:13px;font-weight:600;color:var(--muted);margin:0">{{ title }}</p>
  <p style="font-size:11px;color:var(--muted);opacity:.6;max-width:340px;line-height:1.5;margin:0">{{ hint }}</p>
</div>
{% endmacro %}
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inteligência SEO — Rede Fox</title>
<link rel="icon" type="image/x-icon" href="redefox_favicon.ico">
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
    --bg: #111111; --card: #1a1a1a; --text: #e2e8f0; --muted: #9ca3af;
    --border: #2d2d2d; --input-bg: #111111; --hover: #222222;
    --alert-bg: #3f0000; --alert-border: #e31b23;
    --fox-red: #e31b23; --fox-red-dark: #b51219;
  }
  :root[data-theme="light"] {
    --bg: #f5f5f5; --card: #ffffff; --text: #111111; --muted: #555555;
    --border: #e0e0e0; --input-bg: #ffffff; --hover: #f8f8f8;
    --alert-bg: #fff0f0; --alert-border: #e31b23;
  }
  body { background:var(--bg); color:var(--text); font-family:sans-serif; transition:background .2s,color .2s; }
  .card { background:var(--card); border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,.18); }
  .accent { color:var(--fox-red); }
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
  .dataTables_wrapper .dataTables_paginate .paginate_button.current { background:var(--fox-red) !important; color:#fff !important; border-radius:4px; }
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

{% if alertas %}
<div class="alert-banner mb-6" style="display:flex;align-items:flex-start;gap:10px">
  <svg style="width:16px;height:16px;flex-shrink:0;margin-top:1px;color:#fca5a5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
  <div>{% for banner in alertas %}<p style="font-size:13px;margin:0 0 2px">{{ banner }}</p>{% endfor %}</div>
</div>
{% endif %}

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
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#34d399;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"/></svg>
      Cobertura de Serviços por Cidade
    </h3>
    <div id="chart-cobertura">{% if not disponivel.expansao %}{{ empty_state('Plano de expansão não gerado nesta execução.','Configure ao menos um provedor SERP (BRAVE_SEARCH_KEY, BING_SEARCH_KEY ou TAVILY_API_KEY) e reexecute o pipeline.') }}{% endif %}</div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#3b82f6;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/></svg>
      Saúde Técnica On-Page
    </h3>
    <div id="chart-saude">{% if not disponivel.auditoria %}{{ empty_state('Auditoria técnica indisponível.','O crawler não completou esta execução. Será reprocessado automaticamente na próxima segunda-feira.') }}{% endif %}</div>
  </div>
</div>

<!-- Gráficos linha 2 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="card p-4">
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#e31b23;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0"/></svg>
      Top 10 Concorrentes Locais
    </h3>
    <div id="chart-concorrentes">{% if not disponivel.serp %}{{ empty_state('Dados SERP indisponíveis.','Adicione ao menos uma chave de busca nos Secrets do repositório: BRAVE_SEARCH_KEY (2.000/mês grátis), BING_SEARCH_KEY (1.000/mês grátis) ou TAVILY_API_KEY (1.000/mês grátis).') }}{% endif %}</div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#a78bfa;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941"/></svg>
      Evolução Semanal de KPIs
    </h3>
    <div id="chart-historico"></div>
  </div>
</div>

<!-- Gráficos linha 3 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="card p-4">
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#38bdf8;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/></svg>
      Core Web Vitals (Mobile)
    </h3>
    <div id="chart-vitals">{% if not disponivel.vitals %}{{ empty_state('Core Web Vitals indisponível.','Opcional: adicione PSI_API_KEY nos Secrets para 400 req/dia. Sem chave, usa o limite gratuito de 25 req/dia — será preenchido automaticamente no próximo run.') }}{% endif %}</div>
  </div>
  <div class="card p-4">
    <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
      <svg style="width:14px;height:14px;color:#e31b23;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z"/></svg>
      Share of Voice — Evolução
    </h3>
    <div id="chart-sov"></div>
  </div>
</div>

<!-- Reviews -->
<div class="card p-4 mb-6">
  <h3 class="text-sm font-semibold mb-3" style="color:var(--muted);display:flex;align-items:center;gap:6px">
    <svg style="width:14px;height:14px;color:#fbbf24;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"/></svg>
    Avaliações Google por Unidade
  {% if reviews_disponivel %}
  <div id="chart-reviews"></div>
  {% else %}
  {{ empty_state('Reviews Monitor desativado.','Opcional: adicione PLACES_API_KEY nos Secrets (Google Places API, 200 req/dia grátis) para monitorar as avaliações das 10 unidades no Google Maps.') }}
  {% endif %}
</div>

<!-- Tabela -->
<div class="card p-6 mb-6">
  <h3 class="text-sm font-semibold mb-4" style="color:var(--muted);display:flex;align-items:center;gap:6px">
    <svg style="width:14px;height:14px;color:#34d399;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/></svg>
    Plano de Expansão — Landing Pages
  </h3>
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
const dark = { paper_bgcolor: '#1a1a1a', plot_bgcolor: '#1a1a1a',
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
  const bg = isLight ? '#ffffff' : '#1a1a1a';
  const paperBg = isLight ? '#ffffff' : '#1a1a1a';
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

<!-- Footer -->
<footer style="margin-top:48px;padding:20px 0 28px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
  <span style="font-size:12px;color:var(--muted)">
    &copy; <span id="footer-year"></span> PageUp Sistemas
  </span>
  <a href="https://wa.me/5569993882222" target="_blank" rel="noopener"
     style="display:flex;align-items:center;gap:6px;text-decoration:none;color:var(--muted);font-size:12px;transition:color .15s"
     onmouseover="this.style.color='#25d366'" onmouseout="this.style.color='var(--muted)'">
    <svg style="width:16px;height:16px;flex-shrink:0" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
    </svg>
    (69) 99938-2222
  </a>
</footer>
<script>document.getElementById('footer-year').textContent = new Date().getFullYear();</script>
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
        go.Bar(name="Ausente", x=summary.index.tolist(), y=ausente.tolist(), marker_color="#e31b23"),
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
        marker_colors=["#3b82f6", "#e31b23"],
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
    colors = {"cobertura_local_pct": "#3b82f6", "lps_recomendadas": "#e31b23",
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
        colors = ["#22c55e" if v <= 2.5 else ("#f59e0b" if v <= 4.0 else "#ef4444")
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
            line=dict(color="#e31b23"),
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
            colors.append("#f59e0b")
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
    fig.add_vline(x=4.0, line_dash="dot", line_color="#f59e0b",
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

    disponivel = {
        "auditoria": df_audit is not None,
        "gsc": df_gsc is not None,
        "serp": df_serp is not None,
        "expansao": df_expansion is not None,
        "vitals": df_vitals is not None,
        "reviews": df_reviews is not None,
    }

    alertas = []
    nomes = {"auditoria": "Auditoria Técnica", "gsc": "GSC Performance",
             "serp": "SERP Concorrência", "expansao": "Plano de Expansão"}
    for key, nome in nomes.items():
        if not disponivel[key]:
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
        reviews_disponivel=disponivel["reviews"],
        disponivel=disponivel,
    )

    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(html, encoding="utf-8")
    logger.info("Dashboard gerado em docs/index.html")
