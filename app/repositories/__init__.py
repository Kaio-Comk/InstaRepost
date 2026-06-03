"""Repositórios de acesso a dados."""
from app.repositories.caption_repository import CaptionRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.video_repository import VideoRepository

__all__ = [
    "ProfileRepository",
    "VideoRepository",
    "CaptionRepository",
    "JobRepository",
]
