"""Agendador 24/7: publica 1 vídeo por ciclo, sem repetir.

Lógica de cada ciclo (modo instaloader):
  1. Se NÃO há vídeo pendente de publicação, puxa UMA URL da fila
     (data/queue.txt), baixa e gera a legenda — criando 1 pendente.
  2. Publica EXATAMENTE 1 vídeo pendente (o mais antigo).

Com POLL_INTERVAL_SECONDS=3600 isso resulta em 1 post por hora. Não repete:
  - o banco tem UNIQUE(profile_id, source_post_id);
  - cada vídeo publicado vira published=True (sai da fila de pendentes);
  - cada URL processada é movida para data/queue.done.txt.

No modo manual, processa a pasta data/inbox e publica 1 por ciclo.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from app.config.settings import get_settings
from app.db import init_db, session_scope
from app.models.video import Video
from app.services.pipeline_service import PipelineService
from app.sources.instaloader_source import extract_shortcode
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _enrich_queue(settings) -> None:
    """Descoberta automática: busca Reels novos e adiciona à fila (sem repetir)."""
    if not settings.auto_discovery:
        return
    from app.sources.discovery import InstagrapiDiscovery

    urls = InstagrapiDiscovery().discover(settings.target_username)
    if not urls:
        return

    qpath = settings.url_queue_path
    done = qpath.with_suffix(".done.txt")

    # Já conhecidos: o que está na fila, no done e no banco.
    known: set = set()
    for p in (qpath, done):
        if p.exists():
            known.update(
                ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")
            )
    with session_scope() as session:
        db_codes = set(session.scalars(select(Video.source_post_id)))

    novos = []
    for u in urls:
        if u in known:
            continue
        if f"ig:{extract_shortcode(u)}" in db_codes:
            continue
        novos.append(u)

    if novos:
        qpath.parent.mkdir(parents=True, exist_ok=True)
        with open(qpath, "a", encoding="utf-8") as fh:
            fh.write("\n".join(novos) + "\n")
        logger.info("Descoberta adicionou %d Reel(s) novo(s) à fila.", len(novos))


def _pop_one_url(path: Path) -> Optional[str]:
    """Tira a primeira URL válida da fila, reescreve o arquivo e arquiva em .done."""
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    url, kept = None, []
    for ln in lines:
        s = ln.strip()
        if url is None and s and not s.startswith("#"):
            url = s
            continue
        kept.append(ln)
    if url is None:
        return None
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    done = path.with_suffix(".done.txt")
    with open(done, "a", encoding="utf-8") as fh:
        fh.write(url + "\n")
    return url


def _recently_posted(settings) -> bool:
    """True se o último post foi há menos que ~90% do intervalo (evita rajadas no restart)."""
    f = settings.data_path / "last_post.txt"
    if not f.exists():
        return False
    try:
        last = float(f.read_text(encoding="utf-8").strip())
    except Exception:
        return False
    return (time.time() - last) < settings.poll_interval_seconds * 0.9


def _mark_posted(settings) -> None:
    (settings.data_path / "last_post.txt").write_text(str(time.time()), encoding="utf-8")


def _tick() -> None:
    settings = get_settings()
    pipeline = PipelineService()
    logger.info("⏱️  Ciclo (origem=%s).", settings.source_provider)

    # 0) Descoberta automática enche a fila (se ligada).
    if settings.source_provider == "instaloader":
        _enrich_queue(settings)

    # 1) Garante que exista pelo menos 1 vídeo pendente de publicação.
    if pipeline.has_pending_publish() == 0:
        if settings.source_provider == "instaloader":
            url = _pop_one_url(settings.url_queue_path)
            if url:
                logger.info("Fila -> processando: %s", url)
                pipeline.run_ingestion_urls([url])
            else:
                logger.info("Sem pendentes e fila vazia (%s).", settings.url_queue_path)
        else:
            pipeline.run_ingestion()

    # 2) Publica exatamente 1 (se automático e respeitando o intervalo mínimo).
    if settings.require_manual_approval:
        logger.info("Aprovação manual ligada — publique pelo painel.")
        return

    # Renova o token proativamente (mesmo que não publique neste ciclo).
    if settings.publisher == "instagram_graph":
        from app.publishers.token_store import ensure_fresh

        ensure_fresh()

    if _recently_posted(settings):
        logger.info("Post recente (< intervalo mínimo) — pulando publicação neste ciclo.")
        return

    report = pipeline.publish_one()
    for msg in report.messages:
        logger.info(msg)
    if report.published > 0:
        _mark_posted(settings)


def run_scheduler() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    init_db()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="auto_post",
        max_instances=1,
        coalesce=True,
    )
    logger.info("Scheduler 24/7 ativo: 1 publicação a cada %ds.", settings.poll_interval_seconds)
    _tick()  # primeiro ciclo imediato
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):  # pragma: no cover
        logger.info("Scheduler encerrado.")


if __name__ == "__main__":  # pragma: no cover
    run_scheduler()
