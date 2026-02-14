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
    rows = db.query(Position.ticker, Position.currency).distinct().all()
    tickers = {t for t, _ in rows}
    # Include FX pairs needed for base-currency portfolio monitoring (USD base).
    for _, ccy in rows:
        ccy_up = (ccy or "USD").upper()
        if ccy_up != "USD":
            tickers.add(f"{ccy_up}USD Curncy")

    ticker_list = sorted(tickers)
    total = sum(service.refresh_ticker(db, t, bbg) for t in ticker_list)
    online = bbg is not None
    return {"refreshed_rows": total, "online": online, "tickers": len(ticker_list)}
