"""SQLite database setup and session factory."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./portfolio.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    from backend.domain.portfolio.models import Portfolio, Position  # noqa: F401
    from backend.domain.market_data.models import MarketData  # noqa: F401
    from backend.domain.backtest.models import BacktestRun, BacktestResult  # noqa: F401
    from backend.domain.signals.models import Signal  # noqa: F401
    Base.metadata.create_all(bind=engine)
