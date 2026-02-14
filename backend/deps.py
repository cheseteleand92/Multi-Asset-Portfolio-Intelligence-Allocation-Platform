"""Dependency injection providers."""
from __future__ import annotations
from typing import Generator
from sqlalchemy.orm import Session
from backend.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_bloomberg_client():
    """Return Bloomberg client, or None if unavailable (offline mode)."""
    try:
        from data.bloomberg_interface import BloombergInterface
        return BloombergInterface()
    except Exception:
        return None
