"""Signals service — wraps core/signals.py and provides regime detection.

Adapts actual core/ API:
  - momentum_signal(prices: DataFrame) -> Series  (one value per ticker)
  - mean_reversion_signal(prices: DataFrame) -> Series
  - vol_breakout_signal(prices: DataFrame) -> Series
  - simple_risk_on_off needs two series; we derive regime from a rolling-mean
    heuristic on the equal-weight portfolio return instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.signals import mean_reversion_signal, momentum_signal, vol_breakout_signal


def _returns_to_prices(returns: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct price index from a returns DataFrame."""
    return (1 + returns).cumprod()


def compute_signals(returns: pd.DataFrame) -> dict:
    """Compute per-ticker signals from a returns DataFrame."""
    if returns.empty or len(returns) < 2:
        return {}

    prices = _returns_to_prices(returns)

    # Need enough history for the longest lookback (60 bars for vol_breakout)
    if len(prices) < 60:
        # Fall back to what we can compute
        result: dict = {}
        for ticker in returns.columns:
            result[ticker] = {
                "momentum": float("nan"),
                "mean_reversion": float("nan"),
                "vol_breakout": float("nan"),
            }
        return result

    mom = momentum_signal(prices)
    mr = mean_reversion_signal(prices)
    vb = vol_breakout_signal(prices)

    result = {}
    for ticker in returns.columns:
        result[ticker] = {
            "momentum": float(mom.get(ticker, float("nan"))),
            "mean_reversion": float(mr.get(ticker, float("nan"))),
            "vol_breakout": float(vb.get(ticker, float("nan"))),
        }
    return result


def get_regime(returns: pd.DataFrame) -> dict:
    """Classify market regime from equal-weight portfolio returns.

    Uses a rolling-mean heuristic (20-day MA > 0 → risk_on) since
    simple_risk_on_off requires a separate vol index we don't have.
    """
    if returns.empty or len(returns) < 20:
        return {"regime": "unknown"}

    port_ret = returns.mean(axis=1)
    rolling_mean = port_ret.rolling(20).mean()
    latest = rolling_mean.iloc[-1]

    if np.isnan(latest):
        return {"regime": "unknown"}

    regime = "risk_on" if latest > 0 else "risk_off"
    return {"regime": regime}
