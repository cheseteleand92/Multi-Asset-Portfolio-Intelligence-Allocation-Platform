from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.signals import service
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.models import Position

router = APIRouter(tags=["signals"])


@router.get("/signals")
def get_signals(db: Session = Depends(get_db)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.compute_signals(returns)


@router.get("/signals/regime")
def get_regime(db: Session = Depends(get_db)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.get_regime(returns)
