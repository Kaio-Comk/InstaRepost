"""Repositório de legendas."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.models.caption import Caption
from app.repositories.base import BaseRepository


class CaptionRepository(BaseRepository[Caption]):
    model = Caption

    def latest_for_video(self, video_id: int) -> Optional[Caption]:
        stmt = (
            select(Caption)
            .where(Caption.video_id == video_id)
            .order_by(Caption.id.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()
