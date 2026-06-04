"""Fábrica de publishers."""
from __future__ import annotations

from app.config.settings import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult
from app.publishers.dry_run_publisher import DryRunPublisher


def get_publisher(name: str | None = None) -> Publisher:
    name = (name or get_settings().publisher).lower()

    if name == "dry_run":
        return DryRunPublisher()
    if name == "instagram_graph":
        from app.publishers.instagram_graph_publisher import InstagramGraphPublisher

        return InstagramGraphPublisher()
    if name == "instagrapi":
        from app.publishers.instagrapi_publisher import InstagrapiPublisher

        return InstagrapiPublisher()

    raise ValueError(
        f"PUBLISHER desconhecido: {name!r} (use 'dry_run', 'instagram_graph' ou 'instagrapi')"
    )


__all__ = ["Publisher", "PublishRequest", "PublishResult", "get_publisher"]
