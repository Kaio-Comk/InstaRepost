"""Contrato de publicação."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PublishRequest:
    video_path: Path
    caption: str
    source_url: Optional[str] = None
    public_media_url: Optional[str] = None  # exigido pela API oficial


@dataclass
class PublishResult:
    success: bool
    external_id: Optional[str] = None
    message: str = ""


class Publisher(ABC):
    name: str = "base"

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult:
        raise NotImplementedError

    # Validações comuns reaproveitáveis pelas implementações.
    def validate(self, request: PublishRequest) -> None:
        if not request.video_path or not Path(request.video_path).exists():
            raise ValueError("Arquivo de vídeo inexistente para publicação.")
        caption = (request.caption or "").strip()
        if not caption:
            raise ValueError("Legenda vazia: publicação bloqueada.")
        if len(caption) > 2200:
            raise ValueError("Legenda excede o limite de 2200 caracteres do Instagram.")
