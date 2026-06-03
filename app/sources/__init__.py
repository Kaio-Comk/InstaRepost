"""Fábrica de origens de ingestão (SourceProvider)."""
from __future__ import annotations

from app.config.settings import get_settings
from app.sources.base import RemoteMedia, SourceProvider
from app.sources.manual_source import ManualSource


def get_source_provider(name: str | None = None) -> SourceProvider:
    """Resolve a origem configurada. Default: manual (ToS-safe)."""
    name = (name or get_settings().source_provider).lower()

    if name == "manual":
        return ManualSource()
    if name == "instaloader":
        # Import tardio: o adaptador não-oficial só carrega se explicitamente pedido.
        from app.sources.instaloader_source import InstaloaderSource

        return InstaloaderSource()

    raise ValueError(f"SOURCE_PROVIDER desconhecido: {name!r} (use 'manual' ou 'instaloader')")


__all__ = ["SourceProvider", "RemoteMedia", "get_source_provider"]
