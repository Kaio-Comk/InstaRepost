"""Adaptador NÃO-OFICIAL de ingestão via instaloader.

⚠️  AVISO DE COMPLIANCE
   Esta origem baixa Reels de um perfil usando engenharia reversa do Instagram.
   NÃO faz parte das APIs oficiais da Meta e o uso PODE violar os Termos de
   Serviço. Habilite (SOURCE_PROVIDER=instaloader) apenas para conteúdo que você
   está EXPRESSAMENTE AUTORIZADO a redistribuir, assumindo o risco. Desde ~2023 o
   Instagram bloqueia acesso anônimo: é necessário LOGIN com uma conta — use uma
   conta DESCARTÁVEL, pois automação pode resultar em limitação/ban.

Boas práticas implementadas para reduzir agressividade:
   - autenticação preferencial por SESSÃO salva (lida com 2FA fora do código);
   - baixa apenas vídeos (Reels), ignorando fotos;
   - respeita um limite de itens por execução;
   - deixa o instaloader controlar o rate limit interno.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from app.config.settings import get_settings
from app.sources.base import RemoteMedia, SourceProvider
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class InstaloaderSource(SourceProvider):
    name = "instaloader"

    def __init__(self, max_items: Optional[int] = None, dest_dir: Optional[Path] = None) -> None:
        settings = get_settings()
        self.max_items = max_items or settings.instaloader_max_items
        self.dest_dir = Path(dest_dir or settings.download_path) / "_instaloader"
        self.login_user = settings.instaloader_user.strip()
        self.login_password = settings.instaloader_password.strip()

    def _build_loader(self):
        try:
            import instaloader  # import tardio: dependência opcional
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "instaloader não instalado. Rode `pip install instaloader` ou use "
                "SOURCE_PROVIDER=manual."
            ) from exc

        self.dest_dir.mkdir(parents=True, exist_ok=True)
        loader = instaloader.Instaloader(
            dirname_pattern=str(self.dest_dir),
            download_pictures=False,
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
            quiet=True,
        )
        self._authenticate(instaloader, loader)
        return instaloader, loader

    def _authenticate(self, instaloader, loader) -> None:
        """Autentica via sessão salva (preferido) ou usuário+senha (fallback).

        Sem login, o Instagram responde 403 e nada é coletado. A sessão é criada
        uma vez com `instaloader --login=<user>` (ou no primeiro login com senha)
        e reutilizada nas execuções seguintes.
        """
        if not self.login_user:
            logger.warning(
                "instaloader sem INSTALOADER_USER: acesso anônimo é bloqueado (403) pelo "
                "Instagram. Configure o login para coletar."
            )
            return

        # 1) Tenta carregar a sessão salva pelo CLI do instaloader.
        try:
            loader.load_session_from_file(self.login_user)
            logger.info("instaloader: sessão de @%s carregada.", self.login_user)
            return
        except FileNotFoundError:
            logger.info("instaloader: sem sessão salva para @%s.", self.login_user)
        except Exception as exc:  # sessão corrompida/expirada
            logger.warning("instaloader: falha ao carregar sessão (%s).", exc)

        # 2) Fallback: login com senha (e salva a sessão para reuso).
        if not self.login_password:
            raise RuntimeError(
                f"Sem sessão salva para @{self.login_user} e INSTALOADER_PASSWORD vazio. "
                f"Crie a sessão uma vez com: instaloader --login={self.login_user}"
            )
        try:
            loader.login(self.login_user, self.login_password)
            loader.save_session_to_file()
            logger.info("instaloader: login de @%s OK e sessão salva.", self.login_user)
        except instaloader.exceptions.TwoFactorAuthRequiredException as exc:
            raise RuntimeError(
                "Conta com 2FA: faça o login interativo uma vez com "
                f"`instaloader --login={self.login_user}` para gerar a sessão."
            ) from exc

    def fetch_new(self, target_username: str) -> List[RemoteMedia]:
        instaloader, loader = self._build_loader()
        logger.warning(
            "InstaloaderSource (NÃO-oficial) coletando @%s — confirme autorização de uso.",
            target_username,
        )

        items: List[RemoteMedia] = []
        try:
            profile = instaloader.Profile.from_username(loader.context, target_username)
            for post in profile.get_posts():
                if not post.is_video:
                    continue
                if len(items) >= self.max_items:
                    break

                target = self._locate_video(post.shortcode)
                if target is None:
                    loader.download_post(post, target=self.dest_dir.name)
                    target = self._locate_video(post.shortcode)
                    if target is None:
                        logger.error("Falha ao localizar vídeo baixado de %s", post.shortcode)
                        continue

                items.append(
                    RemoteMedia(
                        source_post_id=f"ig:{post.shortcode}",
                        source_url=f"https://www.instagram.com/reel/{post.shortcode}/",
                        caption=post.caption or "",
                        hashtags=list(post.caption_hashtags or []),
                        local_path=target,
                    )
                )
        except Exception as exc:  # rede / perfil privado / rate limit / 403
            logger.error("InstaloaderSource falhou: %s", exc)

        logger.info("InstaloaderSource: %d Reel(s) coletado(s).", len(items))
        return items

    def _locate_video(self, shortcode: str) -> Optional[Path]:
        matches = sorted(self.dest_dir.glob(f"*{shortcode}*.mp4"))
        return matches[0] if matches else None
