"""Pipeline de ponta a ponta.

Costura monitor -> download -> legenda (e publicação opcional) dentro de jobs
auditáveis. Cada etapa usa sua própria sessão transacional via session_scope.

Decisão de design: o pipeline NÃO publica automaticamente quando
REQUIRE_MANUAL_APPROVAL=true — ele para na geração da legenda e deixa a
aprovação para o painel web. Isso mantém o humano no circuito por padrão.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.ai import get_caption_generator
from app.config.settings import get_settings
from app.db import session_scope
from app.models.job import JobStatus
from app.publishers import get_publisher
from app.repositories import JobRepository, VideoRepository
from app.services.caption_service import CaptionService
from app.services.download_service import DownloadError, DownloadService
from app.services.monitor_service import MonitorService
from app.services.publish_service import PublishService
from app.sources import get_source_provider
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineReport:
    new_videos: int = 0
    processed: int = 0
    failed: int = 0
    published: int = 0
    messages: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.messages.append(msg)
        logger.info(msg)


class PipelineService:
    """Fachada de alto nível usada pelo scheduler, CLI e painel."""

    def run_ingestion(self, username: str | None = None) -> PipelineReport:
        settings = get_settings()
        username = username or settings.target_username
        report = PipelineReport()

        # 1) Monitorar + registrar (uma transação).
        with session_scope() as session:
            jobs = JobRepository(session)
            job = jobs.start("poll")
            try:
                monitor = MonitorService(session, get_source_provider())
                result = monitor.check_profile(username)
                report.new_videos = len(result.new_videos)
                jobs.finish(job, JobStatus.SUCCESS, f"novos={report.new_videos} dup={result.duplicates}")
            except Exception as exc:
                jobs.finish(job, JobStatus.FAILED, str(exc))
                report.log(f"Monitor falhou: {exc}")
                return report

        report.log(f"Ingestão: {report.new_videos} novo(s) vídeo(s).")

        # 2) Processar pendentes: download/validação + legenda.
        self._process_pending(report)
        return report

    def run_ingestion_urls(self, urls: List[str], username: str | None = None) -> PipelineReport:
        """Ingesta Reels específicos por URL (caminho estável p/ o instaloader)."""
        settings = get_settings()
        username = username or settings.target_username
        report = PipelineReport()

        source = get_source_provider()
        if not hasattr(source, "fetch_by_urls"):
            report.log(f"A origem '{source.name}' não suporta ingestão por URL.")
            return report

        media = source.fetch_by_urls(urls)
        with session_scope() as session:
            result = MonitorService(session, source).register_media(username, media)
            report.new_videos = len(result.new_videos)

        report.log(f"Ingestão por URL: {report.new_videos} novo(s) vídeo(s).")
        self._process_pending(report)
        return report

    def _process_pending(self, report: PipelineReport) -> None:
        with session_scope() as session:
            pending_ids = [v.id for v in VideoRepository(session).list_unprocessed()]

        generator = get_caption_generator()
        if pending_ids and not generator.health_check():
            report.log("⚠️  Ollama indisponível — pulando geração de legendas.")

        for vid in pending_ids:
            self._process_one(vid, generator, report)

    def _process_one(self, video_id: int, generator, report: PipelineReport) -> None:
        with session_scope() as session:
            jobs = JobRepository(session)
            job = jobs.start("process")
            videos = VideoRepository(session)
            video = videos.get(video_id)
            if video is None:
                jobs.finish(job, JobStatus.FAILED, "vídeo sumiu")
                return

            try:
                # Download/validação
                outcome = DownloadService().ensure_local(
                    video.source_post_id, video.source_url, video.local_file
                )
                video.local_file = str(outcome.local_file)
                video.size_bytes = outcome.size_bytes

                # Legenda (best-effort: se a IA cair, deixa pendente para retry)
                if generator.health_check():
                    CaptionService(session, generator).generate_for_video(video.id)
                    video.processed = True
                    report.processed += 1
                    jobs.finish(job, JobStatus.SUCCESS, "download+legenda ok")
                else:
                    jobs.finish(job, JobStatus.FAILED, "IA indisponível")

            except DownloadError as exc:
                report.failed += 1
                jobs.finish(job, JobStatus.FAILED, f"download: {exc}")
                report.log(f"Vídeo {video_id}: {exc}")
            except Exception as exc:  # pragma: no cover - defensivo
                report.failed += 1
                jobs.finish(job, JobStatus.FAILED, str(exc))
                report.log(f"Vídeo {video_id} falhou: {exc}")

    def publish_approved(self) -> PipelineReport:
        """Publica todos os vídeos processados, aprovados e ainda não publicados."""
        report = PipelineReport()
        with session_scope() as session:
            pending_ids = [v.id for v in VideoRepository(session).list_pending_publish()]

        publisher = get_publisher()
        for vid in pending_ids:
            with session_scope() as session:
                result = PublishService(session, publisher).publish_video(vid)
                if result.success and result.external_id != "dry-run":
                    report.published += 1
                if not result.success:
                    report.log(f"Vídeo {vid}: {result.message}")
        report.log(f"Publicação: {report.published} publicado(s).")
        return report
