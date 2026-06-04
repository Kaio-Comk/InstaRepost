"""Serviço de geração de legendas (orquestra a IA local + persistência)."""
from __future__ import annotations

from app.ai import CaptionGenerator
from app.config.settings import get_settings
from app.models.caption import Caption
from app.repositories import CaptionRepository, VideoRepository
from app.utils.logging_config import get_logger
from app.utils.validators import ensure_bio_cta

logger = get_logger(__name__)


class CaptionService:
    def __init__(self, session, generator: CaptionGenerator) -> None:
        self.session = session
        self.generator = generator
        self.videos = VideoRepository(session)
        self.captions = CaptionRepository(session)

    def generate_for_video(self, video_id: int, style: str | None = None) -> Caption:
        settings = get_settings()
        style = style or settings.default_caption_style

        video = self.videos.get(video_id)
        if video is None:
            raise ValueError(f"Vídeo {video_id} não encontrado.")

        context = video.source_caption or "(sem descrição original)"
        text = self.generator.generate(
            context=context,
            style=style,
            target_username=video.profile.username if video.profile else "",
        )
        text = ensure_bio_cta(text, settings.bio_cta)  # garante o CTA mesmo se a IA esquecer

        caption = self.captions.add(
            Caption(
                video_id=video.id,
                generated_caption=text,
                style=style,
                model=settings.ollama_model,
                approved=not settings.require_manual_approval,  # auto-aprova se config permitir
            )
        )
        logger.info("Legenda gerada para vídeo %s (estilo=%s, %d chars).", video_id, style, len(text))
        return caption

    def regenerate(self, video_id: int, style: str | None = None) -> Caption:
        """Gera uma nova versão (mantém histórico das anteriores)."""
        return self.generate_for_video(video_id, style)
