"""Repositório base genérico.

Encapsula o acesso ao ORM para que os serviços dependam de uma interface
de persistência, não do SQLAlchemy diretamente (Dependency Inversion).
"""
from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()  # popula PK sem encerrar a transação
        return entity

    def get(self, entity_id: int) -> Optional[T]:
        return self.session.get(self.model, entity_id)

    def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()
