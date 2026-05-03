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
    from backend.domain.backtest import models as backtest_models
    from backend.domain.market_data import models as market_data_models
    from backend.domain.portfolio import models as portfolio_models
    from backend.domain.signals import models as signal_models

    _ = (backtest_models, market_data_models, portfolio_models, signal_models)

    Base.metadata.create_all(bind=engine)
