"""Validações e sanitização reutilizáveis."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, max_len: int = 200) -> str:
    """Normaliza um nome para uso seguro em filesystem."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = _SAFE_NAME_RE.sub("_", name).strip("._")
    return (name or "file")[:max_len]


def validate_extension(path: Path, allowed: Iterable[str]) -> bool:
    return path.suffix.lower() in {e.lower() for e in allowed}


def validate_size(size_bytes: int, min_mb: float, max_mb: float) -> bool:
    mb = size_bytes / (1024 * 1024)
    return min_mb <= mb <= max_mb


def clean_caption(text: str, max_len: int = 2200) -> str:
    """Sanitiza a legenda: remove cercas de markdown e limita ao máximo do Instagram."""
    text = text.strip()
    # Remove blocos ```...``` que alguns modelos adicionam.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    # Remove tags de "thinking" de modelos como qwen3.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text[:max_len]
