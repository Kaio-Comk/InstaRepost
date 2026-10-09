"""Publisher NÃO-OFICIAL via instagrapi (API privada do Instagram).

⚠️  AVISO DE COMPLIANCE / RISCO
   Publica fazendo login como a sua própria conta pela API privada,
   por engenharia reversa. NÃO é a API oficial da Meta. PODE violar os Termos e
   resultar em LIMITAÇÃO ou BAN da conta — que aqui é a sua conta principal.
   Habilitado apenas via PUBLISHER=instagrapi, por sua conta e risco.

Boas práticas para reduzir bloqueios:
   - sessão persistida (não loga do zero toda vez);
   - upload de Reel via clip_upload (não exige URL pública);
   - reuso do mesmo cliente para o lote de publicações.
"""
from __future__ import annotations

from pathlib import Path

from app.config.settings import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class InstagrapiPublisher(Publisher):
    name = "instagrapi"

    def __init__(self) -> None:
        s = get_settings()
        self.user = s.instagrapi_user.strip()
        self.password = s.instagrapi_password.strip()
        self.session_file = s.instagrapi_session_path
        if not self.user or not self.password:
            raise RuntimeError(
                "instagrapi sem credenciais (INSTAGRAPI_USER / INSTAGRAPI_PASSWORD). "
                "Configure-as ou use PUBLISHER=dry_run."
            )
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from instagrapi import Client
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("instagrapi não instalado (pip install instagrapi).") from exc

        cl = Client()
        # Reaproveita sessão salva (reduz challenges/2FA).
        if self.session_file.exists():
            try:
                cl.load_settings(self.session_file)
                logger.info("instagrapi: sessão de @%s carregada.", self.user)
            except Exception as exc:
                logger.warning("instagrapi: sessão inválida (%s), refazendo login.", exc)

        cl.login(self.user, self.password)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        cl.dump_settings(self.session_file)
        self._client = cl
        return cl

    def publish(self, request: PublishRequest) -> PublishResult:
        self.validate(request)
        logger.warning(
            "[instagrapi NÃO-oficial] Publicando em @%s — risco de ban assumido.", self.user
        )
        try:
            cl = self._get_client()
            media = cl.clip_upload(Path(request.video_path), caption=request.caption)
        except Exception as exc:
            logger.error("Falha ao publicar via instagrapi: %s", exc)
            return PublishResult(success=False, message=str(exc))

        code = getattr(media, "code", None) or getattr(media, "pk", "")
        url = f"https://www.instagram.com/reel/{code}/" if code else ""
        logger.info("Publicado via instagrapi: %s", url or media)
        return PublishResult(success=True, external_id=str(code), message=f"Publicado: {url}")
