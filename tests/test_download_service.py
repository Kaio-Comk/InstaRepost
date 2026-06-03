"""Testes do serviço de download/validação."""
from __future__ import annotations

import pytest

from app.services.download_service import DownloadError, DownloadService


def test_adopt_and_validate_local_file(temp_app_env, monkeypatch):
    watch = temp_app_env["watch"]
    src = watch / "reel1.mp4"
    src.write_bytes(b"x" * (100 * 1024))  # 100 KB > min 0.05 MB

    svc = DownloadService()
    outcome = svc.ensure_local("manual:reel1", None, str(src))

    assert outcome.local_file.exists()
    assert outcome.size_bytes == 100 * 1024
    assert outcome.local_file.parent == temp_app_env["downloads"]


def test_rejects_empty_file(temp_app_env):
    src = temp_app_env["watch"] / "empty.mp4"
    src.write_bytes(b"")
    svc = DownloadService()
    with pytest.raises(DownloadError):
        svc.ensure_local("manual:empty", None, str(src))


def test_rejects_bad_extension(temp_app_env):
    src = temp_app_env["watch"] / "doc.txt"
    src.write_bytes(b"x" * (100 * 1024))
    svc = DownloadService()
    with pytest.raises(DownloadError):
        svc.ensure_local("manual:doc", None, str(src))


def test_requires_source(temp_app_env):
    svc = DownloadService()
    with pytest.raises(DownloadError):
        svc.ensure_local("manual:none", None, None)
