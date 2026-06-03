"""Model: legenda gerada pela IA."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Caption(Base, TimestampMixin):
    __tablename__ = "captions"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    generated_caption: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    video: Mapped["Video"] = relationship(back_populates="captions")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Caption id={self.id} video={self.video_id} approved={self.approved}>"
