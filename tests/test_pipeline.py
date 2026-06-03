"""Teste de integração do pipeline ponta a ponta (origem manual + IA mockada)."""
from __future__ import annotations

from tests.conftest import FakeCaptionGenerator


def test_full_pipeline_manual_source(temp_app_env, monkeypatch):
    # 1) Conteúdo autorizado na pasta observada.
    watch = temp_app_env["watch"]
    (watch / "reel_demo.mp4").write_bytes(b"x" * (120 * 1024))
    (watch / "reel_demo.txt").write_text("contexto original do reel", encoding="utf-8")

    # 2) Mocka a IA local em todos os pontos de uso.
    fake = FakeCaptionGenerator()
    import app.services.pipeline_service as pipe
    monkeypatch.setattr(pipe, "get_caption_generator", lambda: fake)

    from app.services.pipeline_service import PipelineService
    service = PipelineService()

    report = service.run_ingestion("autorizado")
    assert report.new_videos == 1
    assert report.processed == 1
    assert report.failed == 0
    assert fake.calls == 1

    # 3) Rodar de novo não deve duplicar (dedup).
    report2 = service.run_ingestion("autorizado")
    assert report2.new_videos == 0

    # 4) Publicação (dry_run; REQUIRE_MANUAL_APPROVAL=false => auto-aprovado).
    pub = service.publish_approved()
    # dry_run não conta como publicado "real", mas não deve registrar erros.
    assert pub.messages and "Publicação" in pub.messages[-1]
