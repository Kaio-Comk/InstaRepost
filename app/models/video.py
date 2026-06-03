"""Model: vídeo detectado/baixado."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Video(Base, TimestampMixin):
    __tablename__ = "videos"
    __table_args__ = (
        # Um mesmo post de origem nunca deve ser inserido duas vezes para o perfil.
        UniqueConstraint("profile_id", "source_post_id", name="uq_video_profile_post"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )

    source_post_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    local_file: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # Contexto original (caption/hashtags da origem) usado pela IA. Não é republicado.
    source_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="videos")  # noqa: F821
    captions: Mapped[List["Caption"]] = relationship(  # noqa: F821
        back_populates="video", cascade="all, delete-orphan", order_by="Caption.id.desc()"
    )

    @property
    def latest_caption(self) -> Optional["Caption"]:  # noqa: F821
        return self.captions[0] if self.captions else None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Video id={self.id} post={self.source_post_id!r} "
            f"processed={self.processed} published={self.published}>"
        )
