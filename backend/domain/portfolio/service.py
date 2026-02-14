from __future__ import annotations
import csv
import io
from sqlalchemy.orm import Session
from backend.domain.portfolio.models import Portfolio, Position
from backend.schemas.portfolio import PortfolioCreate, PositionCreate


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
    pos = db.query(Position).get(position_id)
    if pos:
        db.delete(pos)
        db.commit()


def import_csv(db: Session, portfolio_id: int, content: bytes) -> int:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    count = 0
    for row in reader:
        pos = Position(
            portfolio_id=portfolio_id,
            ticker=row["ticker"].strip(),
            quantity=float(row["quantity"]),
            cost_price=float(row["cost_price"]),
            currency=row.get("currency", "USD").strip(),
            asset_class=row.get("asset_class", "Equity").strip(),
        )
        db.add(pos)
        count += 1
    db.commit()
    return count
