"""Regime detection models for TAA/DAA."""
from __future__ import annotations

import pandas as pd


def simple_risk_on_off(equity_returns: pd.Series, vol_index: pd.Series) -> pd.Series:
    """Rule-based risk regime classifier."""
    aligned = pd.concat([equity_returns, vol_index], axis=1).dropna()
    aligned.columns = ["eq", "vix"]
    return ((aligned["eq"].rolling(20).mean() > 0) & (aligned["vix"] < aligned["vix"].rolling(60).mean())).astype(int)
