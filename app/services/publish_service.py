"""Serviço de publicação: aplica regras de aprovação e delega ao Publisher."""
from __future__ import annotations

from pathlib import Path

from app.config.settings import get_settings
from app.publishers import Publisher, PublishRequest, PublishResult
from app.repositories import CaptionRepository, VideoRepository
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PublishService:
    def __init__(self, session, publisher: Publisher) -> None:
        self.session = session
        self.publisher = publisher
        self.videos = VideoRepository(session)
        self.captions = CaptionRepository(session)

    def publish_video(self, video_id: int) -> PublishResult:
        settings = get_settings()
        video = self.videos.get(video_id)
        if video is None:
            raise ValueError(f"Vídeo {video_id} não encontrado.")
        if video.published:
            return PublishResult(success=True, external_id=None, message="Já publicado.")

        caption = self.captions.latest_for_video(video_id)
        if caption is None:
            return PublishResult(success=False, message="Sem legenda gerada.")

        if settings.require_manual_approval and not caption.approved:
            return PublishResult(success=False, message="Legenda não aprovada — publicação bloqueada.")

        if not video.local_file or not Path(video.local_file).exists():
            return PublishResult(success=False, message="Arquivo local ausente.")

        public_url = None
        if settings.public_media_base_url:
            public_url = f"{settings.public_media_base_url.rstrip('/')}/{Path(video.local_file).name}"

        request = PublishRequest(
            video_path=Path(video.local_file),
            caption=caption.generated_caption,
            source_url=video.source_url,
            public_media_url=public_url,
        )

        result = self.publisher.publish(request)
        if result.success:
            video.published = True
            self.session.flush()
            logger.info("Vídeo %s publicado (%s).", video_id, result.external_id)
        else:
            logger.error("Publicação do vídeo %s falhou: %s", video_id, result.message)
        return result
