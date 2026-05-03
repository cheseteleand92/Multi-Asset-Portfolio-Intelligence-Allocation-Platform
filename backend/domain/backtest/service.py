"""Backtest service — adapts actual BacktestEngine API.

Actual API (backtest/engine.py):
  BacktestEngine(rebalance_freq="ME")
  engine.run(
      asset_returns,
      allocator,
      lookback=252,
      cost_bps=0.0,
      rebalance_threshold=None,
  ) -> BacktestResult
  BacktestResult.nav      : pd.Series  (index=DatetimeIndex)
  BacktestResult.weights  : pd.DataFrame

Actual optimization API (core/optimization.py):
  hierarchical_risk_parity(cov: pd.DataFrame) -> pd.Series  (indexed by ticker)
"""
from __future__ import annotations

import json
from itertools import product

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.domain.backtest.models import BacktestResult as BacktestResultORM
from backend.domain.backtest.models import BacktestRun
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions
from backend.domain.signals.service import get_regime as get_regime_signal
from backtest.engine import BacktestEngine, BacktestResult
from core.optimization import (
    estimate_covariance,
    hierarchical_risk_parity,
    mean_variance_opt,
)
from core.risk_budgeting import RiskBudgetingEngine
from core.risk_engine import information_ratio, max_drawdown


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


def _estimate_window_covariance(
    window_returns: pd.DataFrame,
    covariance_method: str,
) -> pd.DataFrame:
    return estimate_covariance(window_returns, method=covariance_method)


def _wrap_regime_overlay(allocator, params: dict, apply_overlay: bool = True):
    overlay_name = str(params.get("regime_overlay", "none")).strip().lower()
    if not apply_overlay or overlay_name in {"", "none", "off", "false"}:
        return allocator

    risk_on_exposure = max(0.0, float(params.get("risk_on_exposure", 1.0)))
    risk_off_exposure = max(0.0, float(params.get("risk_off_exposure", 0.35)))

    def wrapped(window_returns: pd.DataFrame) -> pd.Series:
        base_weights = allocator(window_returns).reindex(window_returns.columns).fillna(0.0)
        regime = str(get_regime_signal(window_returns).get("regime", "unknown")).lower()
        exposure = risk_off_exposure if regime == "risk_off" else risk_on_exposure
        return base_weights * exposure

    return wrapped


def _hrp_allocator(window_returns: pd.DataFrame, covariance_method: str = "sample") -> pd.Series:
    cov = _estimate_window_covariance(window_returns, covariance_method)
    try:
        w = hierarchical_risk_parity(cov)
    except Exception:
        return _equal_weight_allocator(window_returns)
    return _normalize_weights(w, window_returns.columns)


def _mean_variance_allocator(
    window_returns: pd.DataFrame,
    risk_aversion: float,
    covariance_method: str = "sample",
) -> pd.Series:
    n_assets = len(window_returns.columns)
    if n_assets == 0:
        return pd.Series(dtype=float)
    exp_returns = window_returns.mean()
    cov = _estimate_window_covariance(window_returns, covariance_method)
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


def _erc_allocator(window_returns: pd.DataFrame, covariance_method: str = "sample") -> pd.Series:
    cov = _estimate_window_covariance(window_returns, covariance_method)
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


def _build_allocator(
    strategy_name: str,
    params: dict,
    apply_regime_overlay: bool = True,
):
    covariance_method = str(params.get("covariance_method", "sample"))
    if strategy_name == "hrp":
        def allocator(window_returns: pd.DataFrame) -> pd.Series:
            return _hrp_allocator(window_returns, covariance_method)
    elif strategy_name == "equal_weight":
        allocator = _equal_weight_allocator
    elif strategy_name == "erc":
        def allocator(window_returns: pd.DataFrame) -> pd.Series:
            return _erc_allocator(window_returns, covariance_method)
    elif strategy_name == "mean_variance":
        risk_aversion = float(params.get("risk_aversion", 5.0))
        def allocator(window_returns: pd.DataFrame) -> pd.Series:
            return _mean_variance_allocator(
                window_returns,
                risk_aversion,
                covariance_method,
            )
    else:
        raise ValueError(
            "Unsupported strategy "
            f"'{strategy_name}'. Supported: {', '.join(STRATEGY_LABELS.keys())}"
        )
    return _wrap_regime_overlay(allocator, params, apply_overlay=apply_regime_overlay)


def _load_backtest_returns(db: Session, portfolio_id: int) -> tuple[list[str], pd.DataFrame]:
    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    returns = prices_to_returns(db, tickers)
    return tickers, returns


def _clamp_lookback(lookback: int, returns: pd.DataFrame) -> int:
    return max(1, min(int(lookback), len(returns) - 1))


def _summarize_backtest_run(
    result,
    strategy: str,
    lookback: int,
    cost_bps: float,
    rebalance_threshold: float | None,
    covariance_method: str,
    regime_overlay: str | None,
    risk_on_exposure: float | None,
    risk_off_exposure: float | None,
) -> dict[str, float | int | str | None]:
    total_return = float(result.nav.iloc[-1] / result.nav.iloc[0] - 1.0)
    annualized_return = float((1.0 + result.returns).prod() ** (252 / len(result.returns)) - 1.0)
    annualized_vol = float(result.returns.std() * np.sqrt(252))
    return {
        "strategy": strategy,
        "lookback_days": int(lookback),
        "cost_bps": float(cost_bps),
        "rebalance_threshold": rebalance_threshold,
        "covariance_method": covariance_method,
        "regime_overlay": regime_overlay,
        "risk_on_exposure": risk_on_exposure,
        "risk_off_exposure": risk_off_exposure,
        "final_nav": float(result.nav.iloc[-1]),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_vol": annualized_vol,
        "max_drawdown": float(max_drawdown(result.returns)),
        "average_turnover": float(result.turnover.mean()),
        "total_transaction_cost": float(result.transaction_costs.sum()),
    }


def _coerce_grid(values, default):
    if values is None:
        return [default]
    if isinstance(values, (list, tuple)):
        return list(values)
    return [values]


def _nav_to_returns(nav: pd.Series) -> pd.Series:
    if nav.empty:
        return pd.Series(dtype=float)
    returns = nav.pct_change()
    returns.iloc[0] = nav.iloc[0] / 100.0 - 1.0
    return returns.astype(float)


def _results_to_nav_series(results: list[BacktestResultORM]) -> pd.Series:
    if not results:
        return pd.Series(dtype=float)
    dates = pd.to_datetime([result.date for result in results])
    values = [result.nav for result in results]
    return pd.Series(values, index=dates, dtype=float)


def _results_to_weights_frame(results: list[BacktestResultORM]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    weight_rows = []
    for result in results:
        payload = json.loads(result.weights_json or "{}")
        weight_rows.append(pd.Series(payload, name=pd.Timestamp(result.date), dtype=float))
    return pd.DataFrame(weight_rows).fillna(0.0)


def _active_share_series(
    portfolio_weights: pd.DataFrame,
    benchmark_weights: pd.DataFrame,
) -> pd.Series:
    if portfolio_weights.empty or benchmark_weights.empty:
        return pd.Series(dtype=float)
    aligned_portfolio, aligned_benchmark = portfolio_weights.align(
        benchmark_weights,
        join="outer",
        axis=1,
        fill_value=0.0,
    )
    common_dates = aligned_portfolio.index.intersection(aligned_benchmark.index)
    if common_dates.empty:
        return pd.Series(dtype=float)
    active_share = 0.5 * (
        aligned_portfolio.loc[common_dates] - aligned_benchmark.loc[common_dates]
    ).abs().sum(axis=1)
    return active_share.astype(float)


def _relative_drawdown(active_returns: pd.Series) -> pd.Series:
    relative_nav = (1.0 + active_returns).cumprod()
    peak = relative_nav.cummax()
    return (relative_nav - peak) / peak


def run_backtest(db: Session, portfolio_id: int, params: dict) -> BacktestRun:
    strategy_name = params.get("strategy", "hrp")
    cost_bps = float(params.get("cost_bps", 10))
    lookback = int(params.get("lookback_days", 63))
    rebalance_threshold = params.get("rebalance_threshold")
    if rebalance_threshold is not None:
        rebalance_threshold = float(rebalance_threshold)

    _, returns = _load_backtest_returns(db, portfolio_id)

    if returns.empty:
        raise ValueError("No market data cached for positions — refresh first")
    if len(returns) < 2:
        raise ValueError("Not enough return history for backtest")
    lookback = _clamp_lookback(lookback, returns)

    allocator = _build_allocator(strategy_name, params)
    engine = BacktestEngine(rebalance_freq="ME")
    bt_result = engine.run(
        returns,
        allocator,
        lookback=lookback,
        cost_bps=cost_bps,
        rebalance_threshold=rebalance_threshold,
    )

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
        metrics_on_date = {
            "turnover": float(bt_result.turnover.loc[dt]),
            "transaction_cost": float(bt_result.transaction_costs.loc[dt]),
        }
        db.add(BacktestResultORM(
            run_id=run.id,
            date=dt.date(),
            nav=float(nav_val),
            weights_json=json.dumps(weights_on_date),
            metrics_json=json.dumps(metrics_on_date),
        ))

    db.commit()
    db.refresh(run)
    return run


def build_benchmark_result(
    db: Session,
    portfolio_id: int,
    params: dict,
) -> BacktestResult | None:
    """Run the selected benchmark on the same universe and parameter window."""
    benchmark_id = str(params.get("benchmark", "equal_weight"))
    if benchmark_id == "none":
        return None

    _, returns = _load_backtest_returns(db, portfolio_id)
    if returns.empty or len(returns) < 2:
        return None

    lookback = int(params.get("lookback_days", 63))
    cost_bps = float(params.get("cost_bps", 10))
    rebalance_threshold = params.get("rebalance_threshold")
    if rebalance_threshold is not None:
        rebalance_threshold = float(rebalance_threshold)
    lookback = _clamp_lookback(lookback, returns)

    engine = BacktestEngine(rebalance_freq="ME")
    allocator = _build_allocator(
        benchmark_id,
        params,
        apply_regime_overlay=bool(params.get("benchmark_regime_overlay", False)),
    )
    benchmark = engine.run(
        asset_returns=returns,
        allocator=allocator,
        lookback=lookback,
        cost_bps=cost_bps,
        rebalance_threshold=rebalance_threshold,
    )
    return benchmark


def build_benchmark_nav(
    db: Session,
    portfolio_id: int,
    params: dict,
) -> list[dict[str, float | str]]:
    benchmark = build_benchmark_result(db, portfolio_id, params)
    if benchmark is None:
        return []
    return [{"date": dt.date().isoformat(), "nav": float(nav)} for dt, nav in benchmark.nav.items()]


def build_relative_attribution(
    results: list[BacktestResultORM],
    benchmark_result: BacktestResult | None,
) -> dict[str, object] | None:
    if benchmark_result is None:
        return None

    portfolio_nav = _results_to_nav_series(results)
    if portfolio_nav.empty:
        return None

    aligned_nav = pd.concat(
        [portfolio_nav.rename("portfolio"), benchmark_result.nav.rename("benchmark")],
        axis=1,
    ).dropna()
    if aligned_nav.empty:
        return None

    portfolio_returns = _nav_to_returns(aligned_nav["portfolio"])
    benchmark_returns = _nav_to_returns(aligned_nav["benchmark"])
    active_returns = portfolio_returns - benchmark_returns

    portfolio_weights = _results_to_weights_frame(results).reindex(aligned_nav.index).fillna(0.0)
    benchmark_weights = benchmark_result.weights.reindex(aligned_nav.index).fillna(0.0)
    active_share = _active_share_series(portfolio_weights, benchmark_weights).reindex(
        aligned_nav.index
    ).fillna(0.0)
    relative_drawdown = _relative_drawdown(active_returns)

    summary = {
        "annualized_active_return": float(active_returns.mean() * 252),
        "tracking_error": float(active_returns.std() * np.sqrt(252)),
        "information_ratio": float(information_ratio(portfolio_returns, benchmark_returns)),
        "max_relative_drawdown": float(relative_drawdown.min()),
        "average_active_share": float(active_share.mean()),
        "total_active_return": float(
            aligned_nav["portfolio"].iloc[-1] / aligned_nav["benchmark"].iloc[-1] - 1.0
        ),
    }
    series = [
        {
            "date": dt.date().isoformat(),
            "portfolio_return": float(portfolio_returns.loc[dt]),
            "benchmark_return": float(benchmark_returns.loc[dt]),
            "active_return": float(active_returns.loc[dt]),
            "active_share": float(active_share.loc[dt]),
        }
        for dt in aligned_nav.index
    ]
    return {"summary": summary, "series": series}


def run_backtest_sweep(
    db: Session,
    portfolio_id: int,
    params: dict,
) -> list[dict[str, float | int | str | None]]:
    _, returns = _load_backtest_returns(db, portfolio_id)
    if returns.empty:
        raise ValueError("No market data cached for positions — refresh first")
    if len(returns) < 2:
        raise ValueError("Not enough return history for backtest")

    strategies = _coerce_grid(
        params.get("strategies"),
        params.get("strategy", "hrp"),
    )
    lookbacks = [
        int(item)
        for item in _coerce_grid(
            params.get("lookback_days_grid"),
            params.get("lookback_days", 63),
        )
    ]
    cost_grid = [
        float(item)
        for item in _coerce_grid(
            params.get("cost_bps_grid"),
            params.get("cost_bps", 10.0),
        )
    ]
    threshold_grid = [
        None if item is None else float(item)
        for item in _coerce_grid(
            params.get("rebalance_threshold_grid"),
            params.get("rebalance_threshold"),
        )
    ]
    covariance_grid = [
        str(item)
        for item in _coerce_grid(
            params.get("covariance_method_grid"),
            params.get("covariance_method", "sample"),
        )
    ]
    regime_overlay_grid = [
        str(item)
        for item in _coerce_grid(
            params.get("regime_overlay_grid"),
            params.get("regime_overlay", "none"),
        )
    ]
    risk_on_grid = [
        float(item)
        for item in _coerce_grid(
            params.get("risk_on_exposure_grid"),
            params.get("risk_on_exposure", 1.0),
        )
    ]
    risk_off_grid = [
        float(item)
        for item in _coerce_grid(
            params.get("risk_off_exposure_grid"),
            params.get("risk_off_exposure", 0.35),
        )
    ]

    engine = BacktestEngine(rebalance_freq="ME")
    summaries = []
    for (
        strategy_name,
        lookback,
        cost_bps,
        rebalance_threshold,
        covariance_method,
        regime_overlay,
        risk_on_exposure,
        risk_off_exposure,
    ) in product(
        strategies,
        lookbacks,
        cost_grid,
        threshold_grid,
        covariance_grid,
        regime_overlay_grid,
        risk_on_grid,
        risk_off_grid,
    ):
        combo_params = dict(params)
        combo_params.update({
            "strategy": strategy_name,
            "lookback_days": int(lookback),
            "cost_bps": float(cost_bps),
            "rebalance_threshold": rebalance_threshold,
            "covariance_method": covariance_method,
            "regime_overlay": regime_overlay,
            "risk_on_exposure": float(risk_on_exposure),
            "risk_off_exposure": float(risk_off_exposure),
        })
        allocator = _build_allocator(strategy_name, combo_params)
        effective_lookback = _clamp_lookback(int(lookback), returns)
        result = engine.run(
            returns,
            allocator,
            lookback=effective_lookback,
            cost_bps=float(cost_bps),
            rebalance_threshold=rebalance_threshold,
        )
        summaries.append(
            _summarize_backtest_run(
                result=result,
                strategy=strategy_name,
                lookback=effective_lookback,
                cost_bps=float(cost_bps),
                rebalance_threshold=rebalance_threshold,
                covariance_method=covariance_method,
                regime_overlay=regime_overlay,
                risk_on_exposure=float(risk_on_exposure),
                risk_off_exposure=float(risk_off_exposure),
            )
        )
    return summaries


def backtest_precheck(db: Session, portfolio_id: int, lookback_days: int = 63) -> dict:
    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    if not tickers:
        return {
            "ok": False,
            "reason": "No positions in portfolio.",
            "positions": 0,
            "tickers": [],
            "tickers_with_data": [],
            "tickers_missing_data": [],
            "common_observations": 0,
            "lookback_days": lookback_days,
        }

    returns = prices_to_returns(db, tickers)
    with_data = sorted(list(returns.columns))
    missing = sorted([t for t in tickers if t not in set(with_data)])
    common_obs = int(len(returns))
    enough_history = common_obs >= max(2, int(lookback_days))
    ok = len(missing) == 0 and common_obs >= 2
    reason = ""
    if len(missing) > 0:
        reason = f"Missing market data for {len(missing)} ticker(s)."
    elif common_obs < 2:
        reason = "Not enough aligned return history."
    elif not enough_history:
        reason = f"Aligned history shorter than lookback ({common_obs} < {int(lookback_days)})."

    return {
        "ok": ok,
        "reason": reason,
        "positions": len(positions),
        "tickers": tickers,
        "tickers_with_data": with_data,
        "tickers_missing_data": missing,
        "common_observations": common_obs,
        "lookback_days": int(lookback_days),
        "enough_history_for_lookback": enough_history,
    }
