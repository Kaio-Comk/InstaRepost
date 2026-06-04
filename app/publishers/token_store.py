"""Gestão e refresh automático do token da Instagram Graph API (login por Instagram).

O token de longa duração (60 dias) pode ser renovado pelo endpoint
`ig_refresh_token` (graph.instagram.com), desde que tenha +24h de vida e não
esteja expirado. Cada refresh estende por mais ~60 dias.

O token "vivo" é guardado em data/ig_token.json (fonte de verdade após o 1º uso),
semeado a partir de IG_ACCESS_TOKEN do .env. Para trocar o token manualmente,
atualize o .env E apague data/ig_token.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import requests

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

REFRESH_WHEN_REMAINING_DAYS = 10   # renova quando faltar menos que isso
MIN_AGE_TO_REFRESH_HOURS = 24      # a API exige token com +24h de vida
ASSUMED_LIFETIME_SECONDS = 60 * 86400


def _store_path() -> Path:
    return get_settings().data_path / "ig_token.json"


def _load() -> Optional[dict]:
    p = _store_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover
        return None


def _save(token: str, expires_in: int) -> dict:
    now = time.time()
    data = {"access_token": token, "fetched_at": now, "expires_at": now + expires_in}
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _refresh_host() -> Optional[str]:
    # ig_refresh_token só existe no caminho 'login por Instagram'.
    return "https://graph.instagram.com" if "graph.instagram.com" in get_settings().ig_api_base else None


def get_access_token() -> str:
    data = _load()
    if data and data.get("access_token"):
        return data["access_token"]
    return get_settings().ig_access_token


def status() -> dict:
    """Resumo legível do token (para CLI/monitoramento)."""
    data = _load()
    if not data:
        seed = get_settings().ig_access_token
        return {"seeded": False, "has_env_token": bool(seed)}
    remaining = data["expires_at"] - time.time()
    return {
        "seeded": True,
        "dias_restantes": round(remaining / 86400, 1),
        "renova_em_dias": round((remaining - REFRESH_WHEN_REMAINING_DAYS * 86400) / 86400, 1),
    }


def ensure_fresh(force: bool = False) -> str:
    """Retorna um token válido, renovando automaticamente quando perto de expirar."""
    settings = get_settings()
    data = _load()
    now = time.time()

    # Semeia o store a partir do .env (token recém-gerado no painel ~60 dias).
    if data is None:
        seed = settings.ig_access_token
        if not seed:
            return ""
        data = _save(seed, ASSUMED_LIFETIME_SECONDS)
        logger.info("Token IG inicializado a partir do .env.")

    host = _refresh_host()
    if host is None:
        return data["access_token"]  # caminho FB não usa ig_refresh_token

    remaining = data["expires_at"] - now
    age = now - data.get("fetched_at", now)
    need = force or (remaining < REFRESH_WHEN_REMAINING_DAYS * 86400)
    if not need:
        return data["access_token"]
    if age < MIN_AGE_TO_REFRESH_HOURS * 3600 and not force:
        return data["access_token"]  # ainda novo demais para renovar

    try:
        resp = requests.get(
            f"{host}/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": data["access_token"]},
            timeout=30,
        )
        j = resp.json()
        if resp.status_code == 200 and "access_token" in j:
            new = _save(j["access_token"], int(j.get("expires_in", ASSUMED_LIFETIME_SECONDS)))
            logger.info("Token IG renovado: +%d dias.", int((new["expires_at"] - now) / 86400))
            return new["access_token"]
        logger.error("Falha ao renovar token IG: %s", j)
    except requests.RequestException as exc:
        logger.error("Erro de rede ao renovar token IG: %s", exc)
    return data["access_token"]
