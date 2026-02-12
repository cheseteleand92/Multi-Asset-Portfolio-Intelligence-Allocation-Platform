"""Slippage and transaction cost models."""
from __future__ import annotations

import pandas as pd


def linear_cost(turnover: pd.Series, bps: float = 5.0) -> pd.Series:
    """Linear cost model in basis points applied to turnover."""
    return turnover * bps * 1e-4
