#!/usr/bin/env python3
"""Ponto de entrada (CLI) do InstaRepost.

Comandos:
  init       Cria diretórios e o schema do banco.
  health     Verifica conexões (banco e IA local).
  ingest     Roda um ciclo de ingestão+processamento manual.
  publish    Publica os vídeos aprovados.
  web        Sobe o painel de aprovação (FastAPI).
  scheduler  Roda o agendador em loop (ingestão periódica).

Exemplos:
  python cli.py init
  python cli.py ingest --username perfil_autorizado
  python cli.py web
"""
from __future__ import annotations

import argparse
import sys

from app.ai import get_caption_generator
from app.config.settings import get_settings
from app.db import init_db
from app.services.pipeline_service import PipelineService
from app.utils.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def cmd_init(_args) -> int:
    get_settings().ensure_dirs()
    init_db()
    logger.info("Inicialização concluída (diretórios + schema).")
    return 0


def cmd_health(_args) -> int:
    settings = get_settings()
    init_db()
    ai_ok = get_caption_generator().health_check()
    logger.info("Banco: OK | IA local (%s): %s", settings.ollama_model, "OK" if ai_ok else "INDISPONÍVEL")
    return 0 if ai_ok else 1


def cmd_ingest(args) -> int:
    report = PipelineService().run_ingestion(args.username)
    logger.info(
        "Ingestão: novos=%d processados=%d falhas=%d",
        report.new_videos, report.processed, report.failed,
    )
    return 0


def cmd_fetch(args) -> int:
    report = PipelineService().run_ingestion_urls(args.urls, args.username)
    logger.info(
        "Fetch por URL: novos=%d processados=%d falhas=%d",
        report.new_videos, report.processed, report.failed,
    )
    return 0


def cmd_publish(_args) -> int:
    report = PipelineService().publish_approved()
    logger.info("Publicados: %d", report.published)
    return 0


def cmd_web(_args) -> int:
    from app.web.api import run_web

    run_web()
    return 0


def cmd_scheduler(_args) -> int:
    from app.schedulers.scheduler import run_scheduler

    run_scheduler()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="instarepost", description="InstaRepost CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Cria diretórios e schema").set_defaults(func=cmd_init)
    sub.add_parser("health", help="Checa banco e IA").set_defaults(func=cmd_health)

    p_ing = sub.add_parser("ingest", help="Ciclo de ingestão/processamento")
    p_ing.add_argument("--username", default=None, help="Perfil alvo (default: TARGET_USERNAME)")
    p_ing.set_defaults(func=cmd_ingest)

    p_fetch = sub.add_parser("fetch", help="Baixa Reels específicos por URL e processa")
    p_fetch.add_argument("urls", nargs="+", help="URLs/shortcodes de Reels")
    p_fetch.add_argument("--username", default=None, help="Perfil de origem (default: TARGET_USERNAME)")
    p_fetch.set_defaults(func=cmd_fetch)

    sub.add_parser("publish", help="Publica aprovados").set_defaults(func=cmd_publish)
    sub.add_parser("web", help="Sobe o painel FastAPI").set_defaults(func=cmd_web)
    sub.add_parser("scheduler", help="Roda o agendador").set_defaults(func=cmd_scheduler)
    return parser


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
