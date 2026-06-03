"""Publisher OFICIAL via Instagram Graph API (Content Publishing API).

Este é o caminho compatível com as políticas da Meta. Requisitos:
  - Conta Instagram Professional (Business/Creator) vinculada a uma Página.
  - App da Meta com permissões instagram_basic + instagram_content_publish.
  - IG_USER_ID e IG_ACCESS_TOKEN (token de longa duração) no .env.
  - O vídeo precisa estar acessível por uma URL pública (PUBLIC_MEDIA_BASE_URL),
    pois a API baixa a mídia a partir dessa URL — ela não aceita upload binário direto.

Fluxo da API de Reels:
  1. POST /{ig-user-id}/media           (media_type=REELS, video_url, caption) -> creation_id
  2. (poll) GET /{creation_id}?fields=status_code  até FINISHED
  3. POST /{ig-user-id}/media_publish   (creation_id) -> id do post publicado
"""
from __future__ import annotations

import time

import requests

from app.config.settings import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


class InstagramGraphPublisher(Publisher):
    name = "instagram_graph"

    def __init__(self) -> None:
        s = get_settings()
        self.ig_user_id = s.ig_user_id
        self.access_token = s.ig_access_token
        if not self.ig_user_id or not self.access_token:
            raise RuntimeError(
                "Credenciais da Graph API ausentes (IG_USER_ID / IG_ACCESS_TOKEN). "
                "Configure-as ou use PUBLISHER=dry_run."
            )

    def publish(self, request: PublishRequest) -> PublishResult:
        self.validate(request)

        media_url = request.public_media_url
        if not media_url:
            return PublishResult(
                success=False,
                message=(
                    "A Graph API exige a mídia em URL pública. Defina PUBLIC_MEDIA_BASE_URL "
                    "e exponha o arquivo, preenchendo public_media_url."
                ),
            )

        try:
            creation_id = self._create_container(media_url, request.caption)
            self._wait_until_ready(creation_id)
            post_id = self._publish_container(creation_id)
        except requests.RequestException as exc:
            logger.error("Falha na publicação oficial: %s", exc)
            return PublishResult(success=False, message=str(exc))

        logger.info("Publicado via Graph API. post_id=%s", post_id)
        return PublishResult(success=True, external_id=post_id, message="Publicado.")

    # ---- Passos da API ----
    def _create_container(self, video_url: str, caption: str) -> str:
        resp = requests.post(
            f"{GRAPH_BASE}/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self.access_token,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def _wait_until_ready(self, creation_id: str, attempts: int = 20, delay: int = 6) -> None:
        for _ in range(attempts):
            resp = requests.get(
                f"{GRAPH_BASE}/{creation_id}",
                params={"fields": "status_code", "access_token": self.access_token},
                timeout=30,
            )
            resp.raise_for_status()
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError("Processamento da mídia falhou na Meta.")
            time.sleep(delay)
        raise TimeoutError("Mídia não ficou pronta a tempo na Graph API.")

    def _publish_container(self, creation_id: str) -> str:
        resp = requests.post(
            f"{GRAPH_BASE}/{self.ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": self.access_token},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["id"]
