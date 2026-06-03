"""Serviço de download/validação de mídia.

Para origens que já entregam o arquivo (manual, instaloader), apenas valida e
normaliza o arquivo local. Para origens que fornecem só uma URL, baixa via HTTP
com streaming e tratamento de falhas de rede.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import requests

from app.config.settings import get_settings
from app.utils.logging_config import get_logger
from app.utils.validators import sanitize_filename, validate_extension, validate_size

logger = get_logger(__name__)


@dataclass
class DownloadOutcome:
    local_file: Path
    size_bytes: int


class DownloadError(Exception):
    pass


class DownloadService:
    def __init__(self) -> None:
        s = get_settings()
        self.dest = s.download_path
        self.allowed = s.allowed_extensions
        self.min_mb = s.min_video_mb
        self.max_mb = s.max_video_mb
        self.dest.mkdir(parents=True, exist_ok=True)

    def ensure_local(self, post_id: str, source_url: str | None, local_file: str | None) -> DownloadOutcome:
        """Garante um arquivo local válido para o vídeo, baixando se necessário."""
        if local_file and Path(local_file).exists():
            path = self._adopt_existing(post_id, Path(local_file))
        elif source_url:
            path = self._download_http(post_id, source_url)
        else:
            raise DownloadError(f"Sem arquivo local nem URL para {post_id}.")

        return self._validate(path)

    # ---- internos ----
    def _target_path(self, post_id: str, suffix: str) -> Path:
        return self.dest / f"{sanitize_filename(post_id)}{suffix}"

    def _adopt_existing(self, post_id: str, src: Path) -> Path:
        """Copia o arquivo já presente para o diretório canônico de downloads."""
        target = self._target_path(post_id, src.suffix.lower() or ".mp4")
        if src.resolve() != target.resolve():
            shutil.copy2(src, target)
            logger.info("Arquivo adotado: %s -> %s", src.name, target.name)
        return target

    def _download_http(self, post_id: str, url: str) -> Path:
        target = self._target_path(post_id, ".mp4")
        tmp = target.with_suffix(".part")
        try:
            with requests.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 16):
                        if chunk:
                            fh.write(chunk)
            tmp.replace(target)
            logger.info("Download concluído: %s (%s)", target.name, url)
            return target
        except requests.RequestException as exc:
            tmp.unlink(missing_ok=True)
            raise DownloadError(f"Falha de rede ao baixar {url}: {exc}") from exc

    def _validate(self, path: Path) -> DownloadOutcome:
        if not validate_extension(path, self.allowed):
            raise DownloadError(f"Extensão não permitida: {path.suffix}")
        size = path.stat().st_size
        if size == 0:
            raise DownloadError("Arquivo vazio (download corrompido).")
        if not validate_size(size, self.min_mb, self.max_mb):
            raise DownloadError(
                f"Tamanho fora da faixa permitida: {size/1024/1024:.2f} MB "
                f"(limites {self.min_mb}–{self.max_mb} MB)."
            )
        logger.info("Validação OK: %s (%.2f MB)", path.name, size / 1024 / 1024)
        return DownloadOutcome(local_file=path, size_bytes=size)
