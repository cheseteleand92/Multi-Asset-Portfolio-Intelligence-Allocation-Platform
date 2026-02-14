"""Analytics service — thin wrapper over core/ engines.

Adapts core/risk_engine.py actual API:
  - portfolio_volatility(weights: pd.Series, cov: pd.DataFrame) -> annualised float
  - total_risk_contribution(weights: pd.Series, cov: pd.DataFrame) -> pd.Series
  - historical_var/historical_es(returns: pd.Series, alpha) -> float
  - max_drawdown(returns: pd.Series) -> float
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from core.risk_engine import (
    portfolio_volatility,
    historical_var,
    historical_es,
    max_drawdown,
    total_risk_contribution,
)


def compute_risk(returns: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Compute portfolio risk metrics from asset returns and weights."""
    if returns.empty or not weights:
        return {}

    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}

    rets_aligned = returns[tickers].dropna()
    w_raw = np.array([weights[t] for t in tickers])
    w_norm = w_raw / w_raw.sum()
    w_series = pd.Series(w_norm, index=tickers)
    cov = rets_aligned.cov()

    port_returns = rets_aligned @ w_series

    return {
        "volatility": float(portfolio_volatility(w_series, cov)),
        "var_95": float(historical_var(port_returns, alpha=0.95)),
        "es_95": float(historical_es(port_returns, alpha=0.95)),
        "max_drawdown": float(max_drawdown(port_returns)),
        "trc": {
            t: float(v)
            for t, v in total_risk_contribution(w_series, cov).items()
        },
        "correlation": {
            t: {t2: float(rets_aligned.corr().loc[t, t2]) for t2 in tickers}
            for t in tickers
        },
    }


def compute_nav(returns: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Compute NAV series and performance metrics."""
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}
    w_raw = np.array([weights[t] for t in tickers])
    w_norm = w_raw / w_raw.sum()
    w_series = pd.Series(w_norm, index=tickers)
    port_returns = returns[tickers].dropna() @ w_series
    nav = (1 + port_returns).cumprod()
    return {
        "nav": {d.isoformat(): float(v) for d, v in nav.items()},
        "total_return": float(nav.iloc[-1] - 1) if len(nav) else 0.0,
        "sharpe": float(port_returns.mean() / port_returns.std() * np.sqrt(252))
                  if port_returns.std() > 0 else 0.0,
    }
