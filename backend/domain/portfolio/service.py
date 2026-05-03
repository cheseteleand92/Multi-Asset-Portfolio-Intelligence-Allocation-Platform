from __future__ import annotations

import csv
import io
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.domain.market_data.models import MarketData
from backend.domain.portfolio.models import Portfolio, Position
from backend.schemas.portfolio import PortfolioCreate, PositionCreate, PositionUpdate


def list_portfolios(db: Session) -> list[Portfolio]:
    return db.query(Portfolio).all()


def create_portfolio(db: Session, data: PortfolioCreate) -> Portfolio:
    p = Portfolio(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def get_positions(db: Session, portfolio_id: int) -> list[Position]:
    return db.query(Position).filter_by(portfolio_id=portfolio_id).all()


def add_position(db: Session, portfolio_id: int, data: PositionCreate) -> Position:
    pos = Position(portfolio_id=portfolio_id, **data.model_dump())
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


def delete_position(db: Session, position_id: int) -> None:
    pos = db.get(Position, position_id)
    if pos:
        db.delete(pos)
        db.commit()


def update_position(db: Session, position_id: int, data: PositionUpdate) -> Position | None:
    pos = db.get(Position, position_id)
    if pos is None:
        return None

    payload = data.model_dump()
    pos.ticker = payload["ticker"]
    pos.asset_class = payload["asset_class"]
    pos.quantity = payload["quantity"]
    pos.cost_price = payload["cost_price"]
    pos.currency = payload["currency"]

    db.commit()
    db.refresh(pos)
    return pos


def import_csv(db: Session, portfolio_id: int, content: bytes, replace: bool = False) -> int:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if replace:
        db.query(Position).filter_by(portfolio_id=portfolio_id).delete()

    count = 0
    for row in reader:
        pos = Position(
            portfolio_id=portfolio_id,
            ticker=row["ticker"].strip(),
            quantity=float(row["quantity"]),
            cost_price=float(row["cost_price"]),
            currency=str(row.get("currency") or "USD").strip(),
            asset_class=str(row.get("asset_class") or "Equity").strip(),
        )
        db.add(pos)
        count += 1
    db.commit()
    return count


def seed_demo_etf_portfolio(db: Session, replace: bool = True) -> tuple[Portfolio, int, int]:
    """
    Create or refresh a demo ETF portfolio and seed synthetic daily market data.
    Returns (portfolio, positions_count, seeded_rows).
    """
    name = "Demo ETF Multi-Asset"
    portfolio = db.query(Portfolio).filter_by(name=name).first()
    if portfolio is None:
        portfolio = Portfolio(name=name, description="ETF-based multi-asset demo portfolio")
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    if replace:
        db.query(Position).filter_by(portfolio_id=portfolio.id).delete()

    holdings = [
        {
            "ticker": "SPY US Equity",
            "asset_class": "US Equity",
            "quantity": 120.0,
            "cost_price": 420.0,
            "currency": "USD",
        },
        {
            "ticker": "IEF US Equity",
            "asset_class": "US Treasury",
            "quantity": 200.0,
            "cost_price": 95.0,
            "currency": "USD",
        },
        {
            "ticker": "GLD US Equity",
            "asset_class": "Gold",
            "quantity": 80.0,
            "cost_price": 180.0,
            "currency": "USD",
        },
        {
            "ticker": "VNQ US Equity",
            "asset_class": "REIT",
            "quantity": 100.0,
            "cost_price": 85.0,
            "currency": "USD",
        },
        {
            "ticker": "EEM US Equity",
            "asset_class": "EM Equity",
            "quantity": 110.0,
            "cost_price": 42.0,
            "currency": "USD",
        },
        {
            "ticker": "1306 JT Equity",
            "asset_class": "Japan Equity",
            "quantity": 140.0,
            "cost_price": 2400.0,
            "currency": "JPY",
        },
    ]

    existing = {
        (p.ticker, p.currency, p.asset_class): p
        for p in db.query(Position).filter_by(portfolio_id=portfolio.id).all()
    }
    for h in holdings:
        key = (h["ticker"], h["currency"], h["asset_class"])
        if key in existing:
            pos = existing[key]
            pos.quantity = h["quantity"]
            pos.cost_price = h["cost_price"]
        else:
            db.add(Position(portfolio_id=portfolio.id, **h))
    db.commit()

    dates = pd.bdate_range(end=pd.Timestamp(date.today()), periods=756)
    rng = np.random.default_rng(20260214)
    series_cfg = {
        "SPY US Equity": (0.00035, 0.012),
        "IEF US Equity": (0.00012, 0.005),
        "GLD US Equity": (0.00018, 0.009),
        "VNQ US Equity": (0.00024, 0.011),
        "EEM US Equity": (0.00028, 0.013),
        "1306 JT Equity": (0.00026, 0.012),
        "USDJPY Curncy": (0.00005, 0.004),
    }
    base_levels = {
        "SPY US Equity": 390.0,
        "IEF US Equity": 96.0,
        "GLD US Equity": 170.0,
        "VNQ US Equity": 82.0,
        "EEM US Equity": 40.0,
        "1306 JT Equity": 2100.0,
        "USDJPY Curncy": 138.0,
    }

    seeded_rows = 0
    for ticker, (drift, vol) in series_cfg.items():
        rets = rng.normal(loc=drift, scale=vol, size=len(dates))
        prices = base_levels[ticker] * np.cumprod(1 + rets)
        for dt, px in zip(dates, prices, strict=True):
            row = db.query(MarketData).filter_by(ticker=ticker, date=dt.date()).first()
            if row is None:
                row = MarketData(ticker=ticker, date=dt.date(), close=float(px), source="seed")
                db.add(row)
                seeded_rows += 1
            else:
                row.close = float(px)
                row.source = "seed"
    db.commit()

    positions_count = db.query(Position).filter_by(portfolio_id=portfolio.id).count()
    return portfolio, positions_count, seeded_rows
