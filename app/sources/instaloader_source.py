"""Adaptador NÃO-OFICIAL de ingestão via instaloader.

⚠️  AVISO DE COMPLIANCE
   Esta origem baixa Reels de um perfil público usando engenharia reversa
   do Instagram. NÃO faz parte das APIs oficiais da Meta e o uso PODE violar
   os Termos de Serviço da plataforma. Habilite (SOURCE_PROVIDER=instaloader)
   apenas para conteúdo que você está EXPRESSAMENTE AUTORIZADO a redistribuir,
   assumindo o risco. O núcleo do sistema funciona sem este módulo.

Boas práticas implementadas para reduzir agressividade:
   - somente perfis públicos (sem login forçado);
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

    def __init__(self, max_items: int = 12, dest_dir: Optional[Path] = None) -> None:
        settings = get_settings()
        self.max_items = max_items
        self.dest_dir = Path(dest_dir or settings.download_path) / "_instaloader"

    def _build_loader(self):
        try:
            import instaloader  # import tardio: dependência opcional
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "instaloader não instalado. Rode `pip install instaloader` ou use "
                "SOURCE_PROVIDER=manual."
            ) from exc

        self.dest_dir.mkdir(parents=True, exist_ok=True)
        return instaloader, instaloader.Instaloader(
            dirname_pattern=str(self.dest_dir),
            download_pictures=False,
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
            quiet=True,
        )

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

                target = self.dest_dir / f"{post.shortcode}.mp4"
                if not target.exists():
                    loader.download_post(post, target=self.dest_dir.name)
                    downloaded = self._locate_video(post.shortcode)
                    if downloaded is None:
                        logger.error("Falha ao localizar vídeo baixado de %s", post.shortcode)
                        continue
                    target = downloaded

                items.append(
                    RemoteMedia(
                        source_post_id=f"ig:{post.shortcode}",
                        source_url=f"https://www.instagram.com/reel/{post.shortcode}/",
                        caption=post.caption or "",
                        hashtags=list(post.caption_hashtags or []),
                        local_path=target,
                    )
                )
        except Exception as exc:  # rede / perfil privado / rate limit
            logger.error("InstaloaderSource falhou: %s", exc)

        logger.info("InstaloaderSource: %d Reel(s) coletado(s).", len(items))
        return items

    def _locate_video(self, shortcode: str) -> Optional[Path]:
        matches = sorted(self.dest_dir.glob(f"*{shortcode}*.mp4"))
        return matches[0] if matches else None
