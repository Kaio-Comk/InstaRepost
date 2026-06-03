"""Origem manual: lê vídeos autorizados de uma pasta observada.

Esta é a fonte DEFAULT e 100% compatível com os Termos da Meta: você (ou o
dono do conteúdo) coloca os arquivos autorizados em WATCH_DIR. Um arquivo
``<nome>.txt`` opcional ao lado do vídeo fornece o contexto/legenda original.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from app.config.settings import get_settings
from app.sources.base import RemoteMedia, SourceProvider
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualSource(SourceProvider):
    name = "manual"

    def __init__(self, watch_dir: Path | None = None, allowed_extensions=None) -> None:
        settings = get_settings()
        self.watch_dir = Path(watch_dir or settings.watch_path)
        self.allowed = {e.lower() for e in (allowed_extensions or settings.allowed_extensions)}

    def fetch_new(self, target_username: str) -> List[RemoteMedia]:
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        items: List[RemoteMedia] = []

        for path in sorted(self.watch_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in self.allowed:
                continue

            # post_id estável derivado do nome do arquivo.
            post_id = f"manual:{path.stem}"
            caption = ""
            sidecar = path.with_suffix(".txt")
            if sidecar.exists():
                caption = sidecar.read_text(encoding="utf-8", errors="ignore").strip()

            items.append(
                RemoteMedia(
                    source_post_id=post_id,
                    source_url=None,
                    caption=caption,
                    local_path=path,
                )
            )

        logger.info("ManualSource: %d arquivo(s) encontrado(s) em %s", len(items), self.watch_dir)
        return items
