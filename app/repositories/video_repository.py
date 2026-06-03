"""Repositório de vídeos."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.video import Video
from app.repositories.base import BaseRepository


class VideoRepository(BaseRepository[Video]):
    model = Video

    def get_by_source(self, profile_id: int, source_post_id: str) -> Optional[Video]:
        stmt = select(Video).where(
            Video.profile_id == profile_id, Video.source_post_id == source_post_id
        )
        return self.session.scalars(stmt).first()

    def exists(self, profile_id: int, source_post_id: str) -> bool:
        """Checagem de duplicação usada pelo monitor."""
        return self.get_by_source(profile_id, source_post_id) is not None

    def list_unprocessed(self) -> List[Video]:
        stmt = select(Video).where(Video.processed.is_(False)).order_by(Video.id)
        return list(self.session.scalars(stmt))

    def list_pending_publish(self) -> List[Video]:
        """Vídeos processados (com legenda) ainda não publicados."""
        stmt = (
            select(Video)
            .where(Video.processed.is_(True), Video.published.is_(False))
            .order_by(Video.id)
        )
        return list(self.session.scalars(stmt))
