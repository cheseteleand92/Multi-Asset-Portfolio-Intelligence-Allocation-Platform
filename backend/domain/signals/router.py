from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.models import Position
from backend.domain.signals import service

router = APIRouter(tags=["signals"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/signals")
def get_signals(db: DbSession):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.compute_signals(returns)


@router.get("/signals/regime")
def get_regime(db: DbSession):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.get_regime(returns)
