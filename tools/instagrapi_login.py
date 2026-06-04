#!/usr/bin/env python3
"""Login interativo do instagrapi (gera a sessão de publicação).

POR QUE
   Logar pela primeira vez pode exigir 2FA ou aprovação de "novo login" no app.
   Fazer isso UMA vez aqui (interativo) e salvar a sessão reduz bloqueios depois.

USO (rode VOCÊ MESMO — é a sua conta):
   ./venv/bin/python tools/instagrapi_login.py
   (usa INSTAGRAPI_USER/INSTAGRAPI_PASSWORD do .env; pede o código 2FA se preciso)

Resultado: salva a sessão em data/instagrapi_session.json, que o
InstagrapiPublisher reutiliza nas publicações.
"""
from __future__ import annotations

import sys

from app.config.settings import get_settings


def main() -> int:
    from instagrapi import Client
    from instagrapi.exceptions import TwoFactorRequired

    s = get_settings()
    user = s.instagrapi_user.strip()
    password = s.instagrapi_password.strip()
    if not user or not password:
        sys.exit("Configure INSTAGRAPI_USER e INSTAGRAPI_PASSWORD no .env antes.")

    session_path = s.instagrapi_session_path
    session_path.parent.mkdir(parents=True, exist_ok=True)

    cl = Client()
    if session_path.exists():
        try:
            cl.load_settings(session_path)
            print("Sessão existente carregada — validando…")
        except Exception:
            pass

    try:
        cl.login(user, password)
    except TwoFactorRequired:
        code = input("Código de verificação (2FA): ").strip()
        cl.login(user, password, verification_code=code)

    cl.dump_settings(session_path)
    me = cl.account_info()
    print(f"✅ Logado como @{me.username}. Sessão salva em {session_path}")
    print("Agora: PUBLISHER=instagrapi no .env e rode cli.py publish / scheduler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
