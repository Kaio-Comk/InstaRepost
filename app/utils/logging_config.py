"""Logging profissional: console + arquivo rotativo, formato estruturado."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from app.config.settings import get_settings

_CONFIGURED = False

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(force: bool = False) -> None:
    """Configura o logger raiz uma única vez (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    settings = get_settings()
    log_dir: Path = settings.log_path
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Arquivo rotativo (5 MB x 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "instarepost.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Erros num arquivo dedicado para triagem rápida.
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
