#!/usr/bin/env python3
"""Assistente de setup da Instagram Graph API (publicação oficial).

Faz três coisas a partir de um token de CURTA duração (gerado no
Graph API Explorer) + App ID/Secret:
  1) troca pelo token de LONGA duração (~60 dias);
  2) lista as Páginas do Facebook ligadas e o IG Business Account de cada uma;
  3) imprime exatamente o que colar no .env (IG_USER_ID, IG_ACCESS_TOKEN).

PRÉ-REQUISITOS (uma vez, feitos por você no app/Meta):
  - sua conta do Instagram convertida para Professional (Business/Creator);
  - conta vinculada a uma Página do Facebook;
  - App em developers.facebook.com com a Instagram Graph API;
  - no Graph API Explorer, gerar User Token com as permissões:
      instagram_basic, instagram_content_publish, pages_show_list,
      pages_read_engagement, business_management

USO:
  ./venv/bin/python tools/ig_graph_setup.py \
      --app-id SEU_APP_ID --app-secret SEU_APP_SECRET --token TOKEN_CURTO
"""
from __future__ import annotations

import argparse
import sys

import requests

GRAPH = "https://graph.facebook.com/v19.0"


def _get(path: str, **params) -> dict:
    resp = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        sys.exit(f"Erro da Graph API em /{path}: {data.get('error', data)}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Setup da Instagram Graph API")
    ap.add_argument("--app-id", required=True)
    ap.add_argument("--app-secret", required=True)
    ap.add_argument("--token", required=True, help="Token de curta duração (Graph API Explorer)")
    args = ap.parse_args()

    # 1) Token de longa duração
    ll = _get(
        "oauth/access_token",
        grant_type="fb_exchange_token",
        client_id=args.app_id,
        client_secret=args.app_secret,
        fb_exchange_token=args.token,
    )
    long_token = ll["access_token"]
    print("\n✅ Token de LONGA duração obtido (~60 dias).")

    # 2) Páginas + IG Business Account
    pages = _get("me/accounts", access_token=long_token).get("data", [])
    if not pages:
        sys.exit("Nenhuma Página encontrada. Vincule sua conta do Instagram a uma Página do Facebook.")

    print("\n=== Páginas e contas Instagram vinculadas ===")
    found = []
    for page in pages:
        info = _get(
            page["id"],
            fields="name,instagram_business_account{id,username}",
            access_token=long_token,
        )
        iga = info.get("instagram_business_account")
        line = f"- Página '{info.get('name')}' (id={page['id']})"
        if iga:
            line += f"  ->  IG @{iga.get('username')} (id={iga['id']})"
            found.append(iga)
        print(line)

    if not found:
        sys.exit(
            "\nNenhuma conta IG Business vinculada às Páginas. Confirme a conversão para "
            "Professional e o vínculo com a Página."
        )

    iga = found[0]
    print("\n========================  COLE NO .env  ========================")
    print("PUBLISHER=instagram_graph")
    print(f"IG_USER_ID={iga['id']}")
    print(f"IG_ACCESS_TOKEN={long_token}")
    print("================================================================")
    print("\n⚠️ O token expira em ~60 dias. Rode este script de novo para renovar,")
    print("   ou implemente o refresh automático (endpoint de extensão de token).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
