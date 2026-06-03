"""Testes do serviço de legendas com IA mockada."""
from __future__ import annotations

from app.models.profile import Profile
from app.models.video import Video
from app.repositories import CaptionRepository
from app.services.caption_service import CaptionService


def _seed_video(session) -> Video:
    profile = Profile(username="autorizado")
    session.add(profile)
    session.flush()
    video = Video(
        profile_id=profile.id,
        source_post_id="ig:abc",
        source_caption="contexto original do reel",
    )
    session.add(video)
    session.flush()
    return video


def test_generate_caption_persists(session, fake_ai):
    video = _seed_video(session)
    service = CaptionService(session, fake_ai)

    caption = service.generate_for_video(video.id, style="viral")

    assert caption.id is not None
    assert "viral" in caption.generated_caption
    assert fake_ai.calls == 1
    assert CaptionRepository(session).latest_for_video(video.id).id == caption.id


def test_regenerate_keeps_history(session, fake_ai):
    video = _seed_video(session)
    service = CaptionService(session, fake_ai)

    first = service.generate_for_video(video.id, style="viral")
    second = service.regenerate(video.id, style="informativo")

    assert first.id != second.id
    latest = CaptionRepository(session).latest_for_video(video.id)
    assert latest.id == second.id
    assert "informativo" in second.generated_caption
