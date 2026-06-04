"""Agendador: processa a fila de Reels periodicamente e publica.

Como o Instagram bloqueia a varredura do feed (400), o modo `instaloader`
opera por uma FILA de URLs (`data/queue.txt`, 1 link por linha): você cola os
Reels autorizados e o scheduler, a cada ciclo, baixa → gera legenda → publica
(se a aprovação manual estiver desligada) → move as URLs para `queue.done.txt`.

No modo `manual`, processa a pasta observada (data/inbox) normalmente.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config.settings import get_settings
from app.db import init_db
from app.services.pipeline_service import PipelineService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _read_queue(path: Path) -> List[str]:
    if not path.exists():
        return []
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _drain_queue(path: Path, processed: List[str]) -> None:
    """Move as URLs processadas para queue.done.txt e esvazia a fila."""
    if not processed:
        return
    done = path.with_suffix(".done.txt")
    with open(done, "a", encoding="utf-8") as fh:
        fh.write("\n".join(processed) + "\n")
    path.write_text("", encoding="utf-8")


def _tick() -> None:
    settings = get_settings()
    pipeline = PipelineService()
    logger.info("⏱️  Ciclo iniciado (origem=%s).", settings.source_provider)

    if settings.source_provider == "instaloader":
        queue_path = settings.url_queue_path
        urls = _read_queue(queue_path)
        if urls:
            logger.info("Fila: %d URL(s) para processar.", len(urls))
            pipeline.run_ingestion_urls(urls)
            _drain_queue(queue_path, urls)
        else:
            logger.info("Fila vazia (%s). Cole links de Reels para processar.", queue_path)
    else:
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
