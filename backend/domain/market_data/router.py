from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.deps import get_bloomberg_client, get_db
from backend.domain.market_data import service
from backend.domain.portfolio.models import Position

router = APIRouter(tags=["market_data"])


@router.get("/market-data/{ticker}")
def get_prices(ticker: str, db: Session = Depends(get_db)):
    rows = service.get_cached_prices(db, ticker)
    return [{"date": r.date.isoformat(), "close": r.close} for r in rows]


@router.post("/market-data/refresh")
def refresh_all(db: Session = Depends(get_db), bbg=Depends(get_bloomberg_client)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    total = sum(service.refresh_ticker(db, t, bbg) for t in tickers)
    online = bbg is not None
    return {"refreshed_rows": total, "online": online, "tickers": len(tickers)}
