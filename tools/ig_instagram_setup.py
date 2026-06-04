#!/usr/bin/env python3
"""Setup da publicação oficial — caminho 'Login por Instagram' (graph.instagram.com).

Segundo a doc da Meta, o token gerado no painel do App
(Instagram > "API setup with Instagram business login" > Generate token)
JÁ é de LONGA duração (60 dias). Então o normal é só:
  - colar esse token e o IG User ID no .env.

Este script:
  1) (opcional) se você passar --app-secret e um token de 1h do business login,
     troca pelo token de 60 dias;
  2) busca o seu Instagram User ID via /me;
  3) imprime o que colar no .env.

USO (token do painel, já longo):
  ./venv/bin/python tools/ig_instagram_setup.py --token TOKEN_DO_PAINEL

USO (trocar token curto de 1h por longo):
  ./venv/bin/python tools/ig_instagram_setup.py --app-secret SECRET --token TOKEN_CURTO

REFRESH (renovar antes dos 60 dias, token com +24h de vida):
  GET https://graph.instagram.com/refresh_access_token
      ?grant_type=ig_refresh_token&access_token=SEU_TOKEN_LONGO
"""
from __future__ import annotations

import argparse
import sys

import requests

IG_BASE = "https://graph.instagram.com"
API_VERSION = "v25.0"


def main() -> int:
    ap = argparse.ArgumentParser(description="Setup Instagram login (Content Publishing)")
    ap.add_argument("--token", required=True, help="Token do painel (longo) ou do business login (curto)")
    ap.add_argument("--app-secret", default="", help="Opcional: só para trocar token curto de 1h por longo")
    args = ap.parse_args()

    long_token = args.token

    # 1) Troca opcional (só faz sentido para token curto do business login).
    if args.app_secret:
        resp = requests.get(
            f"{IG_BASE}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": args.app_secret,
                "access_token": args.token,
            },
            timeout=30,
        )
        data = resp.json()
        if resp.status_code == 200 and "access_token" in data:
            long_token = data["access_token"]
            print(f"\n✅ Token de LONGA duração (~{data.get('expires_in', 0)//86400} dias).")
        else:
            msg = data.get("error", {}).get("message", data)
            print(f"\n⚠️  Troca não aplicada ({msg}). Usando o token informado (provavelmente já é longo).")
    else:
        print("\nℹ️  Sem --app-secret: usando o token como está (o do painel já dura 60 dias).")

    # 2) IG User ID via /me
    me = requests.get(
        f"{IG_BASE}/{API_VERSION}/me",
        params={"fields": "user_id,username", "access_token": long_token},
        timeout=30,
    ).json()
    if "error" in me:
        sys.exit(f"Token inválido ao consultar /me: {me['error']}")
    ig_user_id = me.get("user_id") or me.get("id")
    if not ig_user_id:
        sys.exit(f"Não obtive o user_id: {me}")
    print(f"Conta: @{me.get('username', '?')} (IG User ID = {ig_user_id})")

    print("\n========================  COLE NO .env  ========================")
    print("PUBLISHER=instagram_graph")
    print(f"IG_API_BASE={IG_BASE}/{API_VERSION}")
    print(f"IG_USER_ID={ig_user_id}")
    print(f"IG_ACCESS_TOKEN={long_token}")
    print("================================================================")
    print("\nFalta: PUBLIC_MEDIA_BASE_URL apontando para o /media via túnel Cloudflare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
