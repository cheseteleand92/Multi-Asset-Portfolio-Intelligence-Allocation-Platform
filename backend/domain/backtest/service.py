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
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from backtest.engine import BacktestEngine
from core.optimization import hierarchical_risk_parity, mean_variance_opt
from core.risk_budgeting import RiskBudgetingEngine
from backend.domain.backtest.models import BacktestRun
from backend.domain.backtest.models import BacktestResult as BacktestResultORM
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions


def _equal_weight_allocator(window_returns: pd.DataFrame) -> pd.Series:
    n = len(window_returns.columns)
    if n == 0:
        return pd.Series(dtype=float)
    return pd.Series(1.0 / n, index=window_returns.columns)


def _normalize_weights(weights: pd.Series, columns: pd.Index) -> pd.Series:
    clean = weights.reindex(columns).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    total = float(clean.sum())
    if total <= 0:
        return _equal_weight_allocator(pd.DataFrame(columns=columns))
    return clean / total


def _hrp_allocator(window_returns: pd.DataFrame) -> pd.Series:
    cov = window_returns.cov()
    try:
        w = hierarchical_risk_parity(cov)
    except Exception:
        return _equal_weight_allocator(window_returns)
    return _normalize_weights(w, window_returns.columns)


def _mean_variance_allocator(window_returns: pd.DataFrame, risk_aversion: float) -> pd.Series:
    n_assets = len(window_returns.columns)
    if n_assets == 0:
        return pd.Series(dtype=float)
    exp_returns = window_returns.mean()
    cov = window_returns.cov()
    max_weight = max(0.30, 1.0 / n_assets + 1e-4)
    try:
        w = mean_variance_opt(
            exp_returns=exp_returns,
            cov=cov,
            risk_aversion=risk_aversion,
            long_only=True,
            max_weight=max_weight,
        )
    except Exception:
        return _equal_weight_allocator(window_returns)
    return _normalize_weights(w, window_returns.columns)


def _erc_allocator(window_returns: pd.DataFrame) -> pd.Series:
    cov = window_returns.cov()
    try:
        rb = RiskBudgetingEngine()
        result = rb.solve_erc(cov)
        w = result.weights
    except Exception:
        return _equal_weight_allocator(window_returns)
    return _normalize_weights(w, window_returns.columns)


STRATEGY_LABELS = {
    "hrp": "Hierarchical Risk Parity",
    "equal_weight": "Equal Weight",
    "mean_variance": "Mean-Variance",
    "erc": "Equal Risk Contribution",
}


def get_strategies() -> list[dict[str, str]]:
    return [{"id": key, "label": STRATEGY_LABELS[key]} for key in STRATEGY_LABELS]


def get_benchmarks() -> list[dict[str, str]]:
    return [
        {"id": "none", "label": "No Benchmark"},
        {"id": "equal_weight", "label": "Equal Weight"},
        {"id": "hrp", "label": "Hierarchical Risk Parity"},
        {"id": "mean_variance", "label": "Mean-Variance"},
        {"id": "erc", "label": "Equal Risk Contribution"},
    ]


def _build_allocator(strategy_name: str, params: dict):
    if strategy_name == "hrp":
        return _hrp_allocator
    if strategy_name == "equal_weight":
        return _equal_weight_allocator
    if strategy_name == "erc":
        return _erc_allocator
    if strategy_name == "mean_variance":
        risk_aversion = float(params.get("risk_aversion", 5.0))
        return lambda window_returns: _mean_variance_allocator(window_returns, risk_aversion)
    raise ValueError(
        f"Unsupported strategy '{strategy_name}'. Supported: {', '.join(STRATEGY_LABELS.keys())}"
    )


def run_backtest(db: Session, portfolio_id: int, params: dict) -> BacktestRun:
    strategy_name = params.get("strategy", "hrp")
    cost_bps = float(params.get("cost_bps", 10))
    lookback = int(params.get("lookback_days", 63))

    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    returns = prices_to_returns(db, tickers)

    if returns.empty:
        raise ValueError("No market data cached for positions — refresh first")
    if len(returns) < 2:
        raise ValueError("Not enough return history for backtest")
    lookback = max(1, min(lookback, len(returns) - 1))

    allocator = _build_allocator(strategy_name, params)
    engine = BacktestEngine(rebalance_freq="ME")
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


def build_benchmark_nav(db: Session, portfolio_id: int, params: dict) -> list[dict[str, float | str]]:
    """Run equal-weight benchmark on the same universe and parameter window."""
    benchmark_id = str(params.get("benchmark", "equal_weight"))
    if benchmark_id == "none":
        return []

    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    returns = prices_to_returns(db, tickers)
    if returns.empty or len(returns) < 2:
        return []

    lookback = int(params.get("lookback_days", 63))
    cost_bps = float(params.get("cost_bps", 10))
    lookback = max(1, min(lookback, len(returns) - 1))

    engine = BacktestEngine(rebalance_freq="ME")
    allocator = _build_allocator(benchmark_id, params)
    benchmark = engine.run(
        asset_returns=returns,
        allocator=allocator,
        lookback=lookback,
        cost_bps=cost_bps,
    )
    return [{"date": dt.date().isoformat(), "nav": float(nav)} for dt, nav in benchmark.nav.items()]
