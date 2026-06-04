"""Descoberta automática de Reels novos via instagrapi.

Reaproveita a SESSÃO já criada para o instaloader (cookie `sessionid` da conta
belle_fox_fit) — assim não precisa de novo login. Usado pelo scheduler para
encher a fila sozinho quando AUTO_DISCOVERY=true.

⚠️ NÃO-oficial: lista o feed de Reels de um perfil por API privada. Pode violar
   o ToS da Meta e estressar a conta usada. Opt-in, por sua conta e risco.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _instaloader_sessionid(user: str) -> Optional[str]:
    """Extrai o cookie `sessionid` da sessão salva pelo instaloader."""
    path = Path(os.path.expanduser(f"~/.config/instaloader/session-{user}"))
    if not path.exists():
        return None
    try:
        with open(path, "rb") as fh:
            cookies = pickle.load(fh)
        return cookies.get("sessionid")
    except Exception as exc:  # pragma: no cover - sessão corrompida
        logger.warning("Não consegui ler sessionid do instaloader: %s", exc)
        return None


class InstagrapiDiscovery:
    def __init__(self) -> None:
        s = get_settings()
        self.session_user = s.instaloader_user.strip()
        self.amount = s.discovery_amount

    def _client(self):
        from instagrapi import Client

        s = get_settings()
        cl = Client()
        sess = s.data_path / "discovery_session.json"

        # Reaproveita o "device"/sessão salvos (reduz challenges).
        if sess.exists():
            try:
                cl.load_settings(sess)
            except Exception as exc:  # pragma: no cover
                logger.warning("discovery_session inválida (%s).", exc)

        pwd = s.instaloader_password.strip()
        if self.session_user and pwd:
            cl.login(self.session_user, pwd)  # relogin reusa o device carregado
            sess.parent.mkdir(parents=True, exist_ok=True)
            cl.dump_settings(sess)
            return cl

        # Último recurso: cookie sessionid do instaloader (instável).
        sid = _instaloader_sessionid(self.session_user)
        if sid:
            cl.login_by_sessionid(sid)
            return cl
        raise RuntimeError(
            "Sem credenciais para descoberta. Defina INSTALOADER_PASSWORD ou crie a "
            "sessão via tools/import_firefox_session.py."
        )

    def discover(self, username: str) -> List[str]:
        """Retorna URLs dos Reels mais recentes do perfil (mais novo primeiro)."""
        try:
            cl = self._client()
            uid = cl.user_id_from_username(username)
            clips = cl.user_clips(uid, amount=self.amount)
        except Exception as exc:
            logger.error("Descoberta falhou: %s", exc)
            return []

        urls = [
            f"https://www.instagram.com/reel/{m.code}/"
            for m in clips
            if getattr(m, "code", None)
        ]
        logger.info("Descoberta: %d Reel(s) de @%s.", len(urls), username)
        return urls
