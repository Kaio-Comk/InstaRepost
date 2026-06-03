#!/usr/bin/env bash
# Launcher do painel de aprovação do InstaRepost.
# Sobe o FastAPI e abre o navegador no painel.
cd "/home/kaio/Área de trabalho/InstaRepost" || exit 1

# Abre o navegador alguns segundos depois (quando o servidor já está de pé).
( sleep 3 && xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 ) &

venv/bin/python cli.py web

echo ""
read -p "Pressione Enter para fechar..."
