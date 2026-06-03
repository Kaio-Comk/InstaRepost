"""Publisher de simulação: valida e registra, mas não publica de verdade.

Default seguro para desenvolvimento e para operar o pipeline ponta-a-ponta
sem credenciais nem risco de publicação acidental.
"""
from __future__ import annotations

from app.publishers.base import Publisher, PublishRequest, PublishResult
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DryRunPublisher(Publisher):
    name = "dry_run"

    def publish(self, request: PublishRequest) -> PublishResult:
        self.validate(request)
        logger.info(
            "[DRY-RUN] Publicaria %s | legenda (%d chars): %.80s…",
            request.video_path,
            len(request.caption),
            request.caption.replace("\n", " "),
        )
        return PublishResult(success=True, external_id="dry-run", message="Simulado (não publicado).")
