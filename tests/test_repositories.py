"""Testes unitários dos repositórios."""
from __future__ import annotations

from app.models.video import Video
from app.repositories import ProfileRepository, VideoRepository


def test_get_or_create_profile_is_idempotent(session):
    repo = ProfileRepository(session)
    p1 = repo.get_or_create("autorizado")
    p2 = repo.get_or_create("autorizado")
    assert p1.id == p2.id
    assert repo.get_by_username("autorizado") is not None


def test_video_dedup(session):
    profiles = ProfileRepository(session)
    videos = VideoRepository(session)
    profile = profiles.get_or_create("autorizado")

    videos.add(Video(profile_id=profile.id, source_post_id="ig:abc"))
    assert videos.exists(profile.id, "ig:abc") is True
    assert videos.exists(profile.id, "ig:xyz") is False


def test_list_unprocessed_and_pending(session):
    profiles = ProfileRepository(session)
    videos = VideoRepository(session)
    profile = profiles.get_or_create("autorizado")

    v1 = videos.add(Video(profile_id=profile.id, source_post_id="a"))
    v2 = videos.add(Video(profile_id=profile.id, source_post_id="b", processed=True))

    unprocessed = videos.list_unprocessed()
    assert v1 in unprocessed and v2 not in unprocessed

    pending = videos.list_pending_publish()
    assert v2 in pending and v1 not in pending
