"""Backtest service — adapts actual BacktestEngine API.

Actual API (backtest/engine.py):
  BacktestEngine(rebalance_freq="M")
  engine.run(asset_returns, allocator, lookback=252, cost_bps=0.0) -> BacktestResult
  BacktestResult.nav      : pd.Series  (index=DatetimeIndex)
  BacktestResult.weights  : pd.DataFrame

Actual optimization API (core/optimization.py):
  hierarchical_risk_parity(cov: pd.DataFrame) -> pd.Series  (indexed by ticker)
"""
from __future__ import annotations
import json
import pandas as pd
from sqlalchemy.orm import Session
from backtest.engine import BacktestEngine
from core.optimization import hierarchical_risk_parity
from backend.domain.backtest.models import BacktestRun
from backend.domain.backtest.models import BacktestResult as BacktestResultORM
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions


def _hrp_allocator(window_returns: pd.DataFrame) -> pd.Series:
    cov = window_returns.cov()
    return hierarchical_risk_parity(cov)


def _equal_weight_allocator(window_returns: pd.DataFrame) -> pd.Series:
    n = len(window_returns.columns)
    return pd.Series(1.0 / n, index=window_returns.columns)


STRATEGIES = {
    "hrp": _hrp_allocator,
    "equal_weight": _equal_weight_allocator,
}


def run_backtest(db: Session, portfolio_id: int, params: dict) -> BacktestRun:
    strategy_name = params.get("strategy", "hrp")
    cost_bps = float(params.get("cost_bps", 10))
    lookback = int(params.get("lookback_days", 63))

    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    returns = prices_to_returns(db, tickers)

    if returns.empty:
        raise ValueError("No market data cached for positions — refresh first")

    allocator = STRATEGIES.get(strategy_name, _hrp_allocator)
    engine = BacktestEngine(rebalance_freq="M")
    bt_result = engine.run(returns, allocator, lookback=lookback, cost_bps=cost_bps)

    run = BacktestRun(
        portfolio_id=portfolio_id,
        strategy=strategy_name,
        params_json=json.dumps(params),
    )
    db.add(run)
    db.flush()

    for dt, nav_val in bt_result.nav.items():
        weights_on_date = (
            bt_result.weights.loc[dt].to_dict()
            if dt in bt_result.weights.index
            else {}
        )
        db.add(BacktestResultORM(
            run_id=run.id,
            date=dt.date(),
            nav=float(nav_val),
            weights_json=json.dumps(weights_on_date),
        ))

    db.commit()
    db.refresh(run)
    return run
