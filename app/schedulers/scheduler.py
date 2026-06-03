"""Agendador: dispara a ingestão periodicamente.

Usa APScheduler (BlockingScheduler) para rodar o pipeline a cada
POLL_INTERVAL_SECONDS. A publicação automática só ocorre quando a aprovação
manual está desativada — caso contrário, fica a cargo do painel.
"""
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config.settings import get_settings
from app.db import init_db
from app.services.pipeline_service import PipelineService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _tick() -> None:
    settings = get_settings()
    pipeline = PipelineService()
    logger.info("⏱️  Ciclo de ingestão iniciado (@%s).", settings.target_username)
    pipeline.run_ingestion()
    if not settings.require_manual_approval:
        pipeline.publish_approved()


def run_scheduler() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    init_db()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        "interval",
        seconds=settings.poll_interval_seconds,
        next_run_time=None,  # primeiro disparo imediato é feito abaixo
        id="ingestion",
        max_instances=1,
        coalesce=True,
    )
    logger.info("Scheduler ativo: a cada %ds.", settings.poll_interval_seconds)
    _tick()  # execução imediata na subida
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):  # pragma: no cover
        logger.info("Scheduler encerrado.")


if __name__ == "__main__":  # pragma: no cover
    run_scheduler()
