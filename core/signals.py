"""Signal generation for tactical allocation."""
from __future__ import annotations

import pandas as pd


def momentum_signal(prices: pd.DataFrame, lookback: int = 126) -> pd.Series:
    """Cross-sectional momentum signal as trailing total return."""
    return prices.iloc[-1] / prices.iloc[-lookback] - 1


def carry_signal(spot: pd.Series, forward: pd.Series) -> pd.Series:
    """Carry signal for FX/commodities based on implied carry."""
    return (forward / spot) - 1
