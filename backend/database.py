"""Database setup for the UNDERBID Phase 3 backend."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///underbid.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """Create all SQLModel tables registered in metadata."""
    # Importing models here guarantees the table classes are registered before
    # create_all() runs, while avoiding a circular import at module import time.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides one database session per request."""
    with Session(engine) as session:
        yield session
