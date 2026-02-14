from __future__ import annotations
from datetime import date, timedelta
from typing import Any
import pandas as pd
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from backend.domain.market_data.models import MarketData


def get_cached_prices(db: Session, ticker: str) -> list[MarketData]:
    return db.query(MarketData).filter_by(ticker=ticker).order_by(MarketData.date).all()


def upsert_prices(db: Session, ticker: str, rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        stmt = (
            insert(MarketData)
            .values(ticker=ticker, date=row["date"], close=row["close"],
                    volume=row.get("volume"), source="bloomberg")
            .on_conflict_do_update(
                index_elements=["ticker", "date"],
                set_={"close": row["close"], "volume": row.get("volume")}
            )
        )
        db.execute(stmt)
        count += 1
    db.commit()
    return count


def get_last_date(db: Session, ticker: str) -> date | None:
    row = db.query(MarketData).filter_by(ticker=ticker).order_by(
        MarketData.date.desc()).first()
    return row.date if row else None


def refresh_ticker(db: Session, ticker: str, bbg_client: Any | None) -> int:
    """Pull incremental data from Bloomberg. Returns number of rows inserted."""
    if bbg_client is None:
        return 0
    last = get_last_date(db, ticker)
    start = (last + timedelta(days=1)).isoformat() if last else "2020-01-01"
    end = date.today().isoformat()
    if start > end:
        return 0
    try:
        df = bbg_client.bdh([ticker], ["PX_LAST"], start_date=start, end_date=end)
    except Exception:
        return 0
    if df.empty:
        return 0
    # Column name varies by xbbg version:
    # "AAPL US Equity|PX_LAST", "px_last", or just the ticker name.
    # Case-insensitive match; fall back to first column (we only requested PX_LAST).
    col_matches = [c for c in df.columns if "PX_LAST" in str(c).upper()]
    col = col_matches[0] if col_matches else df.columns[0]
    # idx may be datetime.date or pd.Timestamp depending on xbbg version
    rows = [{"date": pd.Timestamp(idx).date(), "close": float(val)}
            for idx, val in df[col].items() if pd.notna(val)]
    return upsert_prices(db, ticker, rows)


def prices_to_returns(db: Session, tickers: list[str]) -> pd.DataFrame:
    """Build a returns DataFrame from cached prices for a list of tickers."""
    frames = {}
    for ticker in tickers:
        rows = get_cached_prices(db, ticker)
        if rows:
            s = pd.Series({r.date: r.close for r in rows}, name=ticker)
            frames[ticker] = s.pct_change().dropna()
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).dropna()
