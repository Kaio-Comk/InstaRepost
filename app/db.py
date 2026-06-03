"""Infraestrutura de banco: engine, sessões e inicialização do schema."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import BASE_DIR, get_settings
from app.models import Base  # importa todos os models (registro no metadata)

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _make_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    connect_args = {}

    if url.startswith("sqlite"):
        # Garante que a pasta do arquivo .db exista.
        # Formato: sqlite:///caminho/relativo.db
        rel = url.split("///", 1)[-1]
        db_path = Path(rel)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        connect_args = {"check_same_thread": False}  # uso em FastAPI/scheduler

    return create_engine(url, echo=False, future=True, connect_args=connect_args)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionFactory


def init_db() -> None:
    """Cria as tabelas (idempotente)."""
    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sessão transacional: commit no sucesso, rollback em erro, sempre fecha."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
