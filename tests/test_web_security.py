"""O túnel expõe a porta do painel: de fora, só /media pode responder."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path))
    from app.config import settings as cfg
    if hasattr(cfg.get_settings, "cache_clear"):
        cfg.get_settings.cache_clear()
    (tmp_path / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    from app.web import api
    monkeypatch.setattr(api.app.router, "on_startup", [])
    return TestClient(api.app)


PELO_TUNEL = {"cf-connecting-ip": "203.0.113.7"}


@pytest.mark.parametrize("metodo,rota", [
    ("get", "/"),
    ("post", "/publish"),
    ("post", "/caption/1/approve"),
    ("post", "/caption/1/edit"),
    ("get", "/video/1"),
])
def test_painel_bloqueado_pelo_tunel(cliente, metodo, rota):
    r = getattr(cliente, metodo)(rota, headers=PELO_TUNEL)
    assert r.status_code == 403


@pytest.mark.parametrize("cab", ["cf-ray", "x-forwarded-for", "x-real-ip"])
def test_qualquer_cabecalho_de_proxy_bloqueia(cliente, cab):
    assert cliente.post("/publish", headers={cab: "1.2.3.4"}).status_code == 403


def test_media_continua_acessivel_pelo_tunel(cliente):
    r = cliente.get("/media/video.mp4", headers=PELO_TUNEL)
    assert r.status_code == 200 and r.content.startswith(b"\x00\x00\x00\x18ftyp")


def test_media_continua_protegida_contra_path_traversal(cliente):
    assert cliente.get("/media/..%2F.env", headers=PELO_TUNEL).status_code == 404


def test_local_continua_passando_pelo_middleware(cliente):
    # sem cabeçalho de proxy = o próprio computador: o middleware não barra
    r = cliente.get("/media/video.mp4")
    assert r.status_code == 200
