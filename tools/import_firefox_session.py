#!/usr/bin/env python3
"""Importa a sessão do Instagram do Firefox para o instaloader.

POR QUE ISSO EXISTE
   O Instagram bloqueia login programático por usuário/senha
   ("Unexpected null login result"). O caminho confiável é reaproveitar a
   sessão de um navegador onde a conta já está logada.

COMO USAR (rode VOCÊ MESMO — lê os cookies do SEU Firefox):
   1) Abra o Firefox e logue em https://www.instagram.com com a conta desejada.
   2) Feche o Firefox (evita lock no cookies.sqlite).
   3) Rode:
        ./venv/bin/python tools/import_firefox_session.py
      (usa INSTALOADER_USER do .env; ou passe: ... import_firefox_session.py belle_fox_fit)

O resultado é um arquivo de sessão em ~/.config/instaloader/session-<user>,
que o InstaloaderSource carrega automaticamente nas próximas execuções.
"""
from __future__ import annotations

import glob
import os
import sqlite3
import sys


def find_cookiefile() -> str:
    candidates = (
        glob.glob(os.path.expanduser("~/.mozilla/firefox/*/cookies.sqlite"))
        + glob.glob(os.path.expanduser("~/snap/firefox/common/.mozilla/firefox/*/cookies.sqlite"))
    )
    if not candidates:
        sys.exit("cookies.sqlite do Firefox não encontrado. Logue no Instagram pelo Firefox antes.")
    # Pega o mais recentemente modificado (perfil em uso).
    return max(candidates, key=os.path.getmtime)


def main() -> int:
    import instaloader

    user = sys.argv[1] if len(sys.argv) > 1 else os.getenv("INSTALOADER_USER", "").strip()
    if not user:
        sys.exit("Informe o usuário: argumento ou INSTALOADER_USER no .env.")

    cookiefile = find_cookiefile()
    print(f"Lendo cookies de: {cookiefile}")
    conn = sqlite3.connect(f"file:{cookiefile}?immutable=1", uri=True)
    try:
        rows = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com%'"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        sys.exit("Nenhum cookie do instagram.com no Firefox. Logue no site primeiro.")

    loader = instaloader.Instaloader(max_connection_attempts=1)
    loader.context._session.cookies.update(rows)

    logged_user = loader.test_login()
    if not logged_user:
        sys.exit("Cookies presentes mas a sessão não está autenticada. Refaça o login no Firefox.")
    if logged_user.lower() != user.lower():
        print(f"⚠️  Atenção: a sessão do Firefox é de @{logged_user}, não @{user}.")
        user = logged_user

    loader.context.username = logged_user
    session_path = os.path.expanduser(f"~/.config/instaloader/session-{user}")
    os.makedirs(os.path.dirname(session_path), exist_ok=True)
    loader.save_session_to_file(session_path)
    print(f"✅ Sessão de @{user} salva em {session_path}")
    print("Agora rode:  ./venv/bin/python cli.py ingest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
