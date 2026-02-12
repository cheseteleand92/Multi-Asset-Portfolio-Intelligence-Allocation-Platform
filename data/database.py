"""SQLAlchemy ORM schema for portfolio intelligence platform."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    """Declarative base."""


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    weight: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    traded_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)


class FactorExposure(Base):
    __tablename__ = "factor_exposures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    factor: Mapped[str] = mapped_column(String(64), index=True)
    exposure: Mapped[float] = mapped_column(Float)


class HistoricalRisk(Base):
    __tablename__ = "historical_risk"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)


class SignalHistory(Base):
    __tablename__ = "signal_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    signal_name: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)


class BenchmarkData(Base):
    __tablename__ = "benchmark_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    benchmark: Mapped[str] = mapped_column(String(64), index=True)
    return_value: Mapped[float] = mapped_column(Float)


def create_session(db_url: str = "sqlite:///portfolio.db"):
    """Create a SQLAlchemy session factory and initialize schema."""
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)
