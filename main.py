import logging
import multiprocessing
import shutil
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src import (
    crawler_site,
    gsc_auditor,
    serp_scanner,
    core_web_vitals,
    gap_analyzer,
    reviews_monitor,
    indexing_pusher,
    catalogo_insights,
    dashboard_builder,
)


def _backup_outputs():
    backup_dir = Path("output/backup") / datetime.now().strftime("%Y-%m-%d")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for csv in Path("output").glob("*.csv"):
        shutil.copy2(csv, backup_dir / csv.name)
    for f in Path("output").glob("*.json"):
        shutil.copy2(f, backup_dir / f.name)


def _run_with_timeout(fn, timeout_seconds: int, nome: str):
    p = multiprocessing.Process(target=fn)
    p.start()
    p.join(timeout=timeout_seconds)
    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError(f"{nome} excedeu {timeout_seconds}s e foi encerrado.")


def _gerar_relatorio(resultados: dict):
    Path("output").mkdir(exist_ok=True)

    # Ler KPIs dos CSVs gerados
    paginas = 0
    cobertura = 0.0
    lps = 0
    sem_schema = 0

    try:
        import pandas as pd
        df_audit = pd.read_csv("output/1_auditoria_tecnica_site.csv", encoding="utf-8")
        paginas = len(df_audit)
        sem_schema = int(df_audit["tem_schema"].eq(False).sum()) if "tem_schema" in df_audit.columns else 0
    except Exception:
        pass

    try:
        import pandas as pd
        df_exp = pd.read_csv("output/4_plano_expansao_landing_pages.csv", encoding="utf-8")
        total = len(df_exp)
        existe = int(df_exp[df_exp["Status_Atual"] == "existe"].shape[0])
        lps = int(df_exp[df_exp["Status_Atual"] != "existe"].shape[0])
        cobertura = round(existe / total * 100, 1) if total else 0.0
    except Exception:
        pass

    # Top 5 oportunidades
    top5_txt = ""
    try:
        import pandas as pd
        df_exp = pd.read_csv("output/4_plano_expansao_landing_pages.csv", encoding="utf-8")
        top5 = df_exp[df_exp["Status_Atual"] != "existe"].head(5)
        rows = ["| Cidade | Serviço | URL Sugerida |", "|---|---|---|"]
        for _, row in top5.iterrows():
            rows.append(f"| {row['Cidade']} | {row['Servico']} | {row['URL_Sugerida']} |")
        top5_txt = "\n".join(rows)
    except Exception:
        top5_txt = "Dados indisponíveis."

    linhas_status = "\n".join(
        f"| {nome} | {status} | {str(dur).split('.')[0]} |"
        for nome, (status, dur) in resultados.items()
    )

    relatorio = f"""# Relatório Executivo — Rede Fox SEO Engine
**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

## Resumo de KPIs
- Páginas mapeadas: {paginas}
- Cobertura local: {cobertura}%
- Landing pages recomendadas: {lps}
- Páginas sem Schema.org: {sem_schema}

## Status dos Módulos
| Módulo | Status | Duração |
|---|---|---|
{linhas_status}

## Top 5 Oportunidades de Expansão
{top5_txt}
"""
    Path("output/RELATORIO_EXECUTIVO.md").write_text(relatorio, encoding="utf-8")
    logger.info("Relatório executivo salvo em output/RELATORIO_EXECUTIVO.md")


def main():
    logger.info("=" * 60)
    logger.info("Fox SEO Engine — Iniciando pipeline")
    logger.info("=" * 60)

    _backup_outputs()

    etapas = [
        ("crawler_site",      crawler_site.run,      600),
        ("gsc_auditor",       gsc_auditor.run,        300),
        ("serp_scanner",      serp_scanner.run,      1200),
        ("core_web_vitals",   core_web_vitals.run,    300),
        ("gap_analyzer",      gap_analyzer.run,       120),
        ("reviews_monitor",   reviews_monitor.run,    120),
        ("indexing_pusher",   indexing_pusher.run,    120),
        ("catalogo_insights", catalogo_insights.run,   60),
        ("dashboard_builder", dashboard_builder.run,  120),
    ]

    resultados = {}
    for nome, fn, timeout in etapas:
        logger.info(f"▶ Iniciando: {nome}")
        t0 = datetime.now()
        try:
            _run_with_timeout(fn, timeout, nome)
            dur = datetime.now() - t0
            resultados[nome] = ("✅ OK", dur)
            logger.info(f"✅ {nome} concluído em {str(dur).split('.')[0]}")
        except TimeoutError as e:
            dur = datetime.now() - t0
            resultados[nome] = ("⏱ Timeout", dur)
            logger.error(str(e))
        except Exception as e:
            dur = datetime.now() - t0
            resultados[nome] = ("❌ Falhou", dur)
            logger.error(f"{nome} falhou: {e}", exc_info=True)

    _gerar_relatorio(resultados)

    logger.info("=" * 60)
    logger.info("Pipeline concluído.")
    for nome, (status, dur) in resultados.items():
        logger.info(f"  {status} {nome} ({str(dur).split('.')[0]})")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Pipeline interrompido pelo usuário.")
        sys.exit(0)
