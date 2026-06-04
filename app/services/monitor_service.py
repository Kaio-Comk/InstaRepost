"""Serviço de monitoramento: detecta novos conteúdos e registra no banco.

Responsabilidades (Single Responsibility):
  - consultar a origem (SourceProvider);
  - deduplicar contra o banco (profile_id + source_post_id);
  - persistir novos vídeos como não-processados.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.repositories import ProfileRepository, VideoRepository
from app.models.video import Video
from app.sources import RemoteMedia, SourceProvider
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MonitorResult:
    new_videos: List[int]      # ids inseridos
    duplicates: int


class MonitorService:
    def __init__(self, session, source: SourceProvider) -> None:
        self.session = session
        self.source = source
        self.profiles = ProfileRepository(session)
        self.videos = VideoRepository(session)

    def check_profile(self, username: str) -> MonitorResult:
        profile = self.profiles.get_or_create(username)
        if not profile.active:
            logger.info("Perfil @%s inativo — ignorando.", username)
            return MonitorResult(new_videos=[], duplicates=0)

        found: List[RemoteMedia] = self.source.fetch_new(username)
        return self.register_media(username, found)

    def register_media(self, username: str, found: List[RemoteMedia]) -> MonitorResult:
        """Deduplica e persiste uma lista de mídias para o perfil (feed ou por URL)."""
        profile = self.profiles.get_or_create(username)
        new_ids: List[int] = []
        duplicates = 0

        for media in found:
            if self.videos.exists(profile.id, media.source_post_id):
                duplicates += 1
                continue

            video = self.videos.add(
                Video(
                    profile_id=profile.id,
                    source_post_id=media.source_post_id,
                    source_url=media.source_url,
                    local_file=str(media.local_path) if media.local_path else None,
                    source_caption=media.context_for_ai,
                )
            )
            new_ids.append(video.id)
            logger.info("Novo vídeo registrado: id=%s post=%s", video.id, media.source_post_id)

        logger.info(
            "Monitor @%s: %d novo(s), %d duplicado(s).", username, len(new_ids), duplicates
        )
        return MonitorResult(new_videos=new_ids, duplicates=duplicates)
