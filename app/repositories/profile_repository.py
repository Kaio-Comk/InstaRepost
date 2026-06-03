"""Repositório de perfis."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    model = Profile

    def get_by_username(self, username: str) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.username == username)
        return self.session.scalars(stmt).first()

    def get_or_create(self, username: str, active: bool = True) -> Profile:
        existing = self.get_by_username(username)
        if existing:
            return existing
        return self.add(Profile(username=username, active=active))

    def list_active(self) -> List[Profile]:
        stmt = select(Profile).where(Profile.active.is_(True))
        return list(self.session.scalars(stmt))
