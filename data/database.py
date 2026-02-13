"""SQLAlchemy ORM schema for portfolio intelligence platform."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Declarative base."""


class Position(Base):
    """Current/point-in-time holdings."""

    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True, default="MAIN")
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    asset_class: Mapped[str] = mapped_column(String(32), index=True, default="UNKNOWN")
    region: Mapped[str] = mapped_column(String(32), index=True, default="GLOBAL")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)


class Trade(Base):
    """Executed trade history."""

    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    traded_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True, default="MAIN")
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(8), default="BUY")
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)


class PortfolioSnapshot(Base):
    """Portfolio-level NAV and performance snapshot."""

    __tablename__ = "portfolio_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True, default="MAIN")
    nav: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_base_ccy: Mapped[float] = mapped_column(Float, default=0.0)
    gross_exposure: Mapped[float] = mapped_column(Float, default=0.0)
    net_exposure: Mapped[float] = mapped_column(Float, default=0.0)


class FactorExposure(Base):
    """Asset-level factor exposures."""

    __tablename__ = "factor_exposures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True, default="MAIN")
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    factor: Mapped[str] = mapped_column(String(64), index=True)
    exposure: Mapped[float] = mapped_column(Float)


class HistoricalRisk(Base):
    """Risk history such as VaR, ES, TE, and volatility."""

    __tablename__ = "historical_risk"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True, default="MAIN")
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)


class SignalHistory(Base):
    """Stored tactical and regime signal time series."""

    __tablename__ = "signal_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    signal_name: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)


class BenchmarkReturn(Base):
    """Benchmark return series."""

    __tablename__ = "benchmark_returns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True)
    benchmark: Mapped[str] = mapped_column(String(64), index=True)
    return_value: Mapped[float] = mapped_column(Float)


def create_session(db_url: str = "sqlite:///portfolio.db"):
    """Create a SQLAlchemy session factory and initialize schema."""
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)
