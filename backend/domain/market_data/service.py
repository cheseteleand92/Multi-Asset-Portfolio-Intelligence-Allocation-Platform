from __future__ import annotations
from datetime import date, timedelta
from typing import Any
import numpy as np
import pandas as pd
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from backend.domain.market_data.models import MarketData


def _price_series(db: Session, ticker: str) -> pd.Series | None:
    rows = get_cached_prices(db, ticker)
    if not rows:
        return None
    series = pd.Series({r.date: r.close for r in rows}, name=ticker).sort_index()
    series.index = pd.to_datetime(series.index)
    return series


def _fx_pair_candidates(currency: str, base_currency: str) -> list[tuple[str, bool]]:
    """
    Returns [(ticker, is_direct_local_to_base)] candidates.
    """
    ccy = currency.upper()
    base = base_currency.upper()
    if ccy == base:
        return []
    return [
        (f"{ccy}{base} Curncy", True),
        (f"{base}{ccy} Curncy", False),
    ]


def _fx_series_local_to_base(db: Session, currency: str, base_currency: str) -> tuple[pd.Series | None, str | None]:
    ccy = currency.upper()
    base = base_currency.upper()
    if ccy == base:
        return pd.Series(dtype=float), None

    for ticker, is_direct in _fx_pair_candidates(ccy, base):
        s = _price_series(db, ticker)
        if s is None or s.empty:
            continue
        if is_direct:
            return s.rename(f"{ccy}->{base}"), ticker
        # Inverse pair found (e.g., USDJPY for JPY->USD).
        inv = (1.0 / s).replace([np.inf, -np.inf], np.nan).dropna()
        return inv.rename(f"{ccy}->{base}"), ticker
    return None, None


def position_values_base(
    db: Session,
    positions: list[Any],
    base_currency: str = "USD",
) -> tuple[dict[str, float], list[str], dict[str, str]]:
    """
    Convert current position market values into base currency.
    """
    values: dict[str, float] = {}
    warnings: list[str] = []
    fx_used: dict[str, str] = {}

    for p in positions:
        price_series = _price_series(db, p.ticker)
        latest_price = float(price_series.iloc[-1]) if price_series is not None and not price_series.empty else float(p.cost_price)
        if price_series is None or price_series.empty:
            warnings.append(f"{p.ticker}: missing market price, fallback to cost_price.")

        fx_series, fx_ticker = _fx_series_local_to_base(db, p.currency, base_currency)
        if p.currency.upper() == base_currency.upper():
            fx = 1.0
        elif fx_series is not None and not fx_series.empty:
            fx = float(fx_series.iloc[-1])
            fx_used[p.currency.upper()] = fx_ticker or f"{p.currency.upper()}{base_currency.upper()} synthetic"
        else:
            fx = 1.0
            warnings.append(
                f"{p.ticker}: FX series for {p.currency.upper()}->{base_currency.upper()} not found, assuming 1.0."
            )

        # Aggregate by ticker to support multiple lots of the same symbol.
        values[p.ticker] = values.get(p.ticker, 0.0) + (float(p.quantity) * latest_price * fx)

    return values, warnings, fx_used


def position_valuation_breakdown(
    db: Session,
    positions: list[Any],
    base_currency: str = "USD",
) -> tuple[list[dict[str, Any]], list[str], dict[str, str]]:
    """
    Return per-position valuation details in both local and base currency.
    """
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    fx_used: dict[str, str] = {}

    for p in positions:
        price_series = _price_series(db, p.ticker)
        latest_price = float(price_series.iloc[-1]) if price_series is not None and not price_series.empty else float(p.cost_price)
        price_date = str(price_series.index[-1].date()) if price_series is not None and not price_series.empty else None
        if price_series is None or price_series.empty:
            warnings.append(f"{p.ticker}: missing market price, fallback to cost_price.")

        fx_series, fx_ticker = _fx_series_local_to_base(db, p.currency, base_currency)
        fx_date: str | None = None
        if p.currency.upper() == base_currency.upper():
            fx_rate = 1.0
        elif fx_series is not None and not fx_series.empty:
            fx_rate = float(fx_series.iloc[-1])
            fx_date = str(fx_series.index[-1].date())
            fx_used[p.currency.upper()] = fx_ticker or f"{p.currency.upper()}{base_currency.upper()} synthetic"
        else:
            fx_rate = 1.0
            warnings.append(
                f"{p.ticker}: FX series for {p.currency.upper()}->{base_currency.upper()} not found, assuming 1.0."
            )

        qty = float(p.quantity)
        local_value = qty * latest_price
        base_value = local_value * fx_rate
        rows.append({
            "position_id": getattr(p, "id", None),
            "ticker": p.ticker,
            "quantity": qty,
            "currency": p.currency.upper(),
            "base_currency": base_currency.upper(),
            "price_local": latest_price,
            "price_date": price_date,
            "fx_rate_local_to_base": fx_rate,
            "fx_ticker": fx_ticker,
            "fx_date": fx_date,
            "value_local": local_value,
            "value_base": base_value,
        })

    return rows, warnings, fx_used


def positions_to_base_returns(
    db: Session,
    positions: list[Any],
    base_currency: str = "USD",
) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    """
    Build position return series in base currency (asset local return + FX return).
    """
    frames: dict[str, pd.Series] = {}
    warnings: list[str] = []
    fx_used: dict[str, str] = {}

    for p in positions:
        local_prices = _price_series(db, p.ticker)
        if local_prices is None or local_prices.empty:
            warnings.append(f"{p.ticker}: no market data.")
            continue

        local_returns = local_prices.pct_change().dropna()
        if p.currency.upper() == base_currency.upper():
            base_returns = local_returns
        else:
            fx_series, fx_ticker = _fx_series_local_to_base(db, p.currency, base_currency)
            if fx_series is None or fx_series.empty:
                warnings.append(
                    f"{p.ticker}: FX series for {p.currency.upper()}->{base_currency.upper()} not found; using local returns."
                )
                base_returns = local_returns
            else:
                fx_used[p.currency.upper()] = fx_ticker or f"{p.currency.upper()}{base_currency.upper()} synthetic"
                fx_returns = fx_series.pct_change().dropna()
                aligned = pd.concat([local_returns.rename("asset"), fx_returns.rename("fx")], axis=1).dropna()
                base_returns = (1.0 + aligned["asset"]) * (1.0 + aligned["fx"]) - 1.0

        frames[p.ticker] = base_returns.rename(p.ticker)

    if not frames:
        return pd.DataFrame(), warnings, fx_used
    out = pd.DataFrame(frames).dropna(how="any").sort_index()
    out.index = pd.to_datetime(out.index)
    return out, warnings, fx_used


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
            s.index = pd.to_datetime(s.index)
            frames[ticker] = s.pct_change().dropna()
    if not frames:
        return pd.DataFrame()
    out = pd.DataFrame(frames).dropna()
    out.index = pd.to_datetime(out.index)
    return out.sort_index()
