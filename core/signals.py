"""Signal generation for tactical allocation."""
from __future__ import annotations

import pandas as pd


def momentum_signal(prices: pd.DataFrame, lookback: int = 126) -> pd.Series:
    """Cross-sectional momentum signal as trailing total return."""
    return prices.iloc[-1] / prices.iloc[-lookback] - 1


def carry_signal(spot: pd.Series, forward: pd.Series) -> pd.Series:
    """Carry signal for FX/commodities based on implied carry."""
    return (forward / spot) - 1


def mean_reversion_signal(prices: pd.DataFrame, window: int = 20) -> pd.Series:
    """Z-score signal: (price - mean) / std. Negative z-score implies buy."""
    roll = prices.rolling(window=window)
    mu = roll.mean().iloc[-1]
    sigma = roll.std().iloc[-1]
    z = (prices.iloc[-1] - mu) / sigma
    return -z  # Invert so high z (overbought) is negative signal


def vol_breakout_signal(prices: pd.DataFrame, short_window: int = 20, long_window: int = 60) -> pd.Series:
    """Volatility breakout: Short-term vol / Long-term vol - 1."""
    ret = prices.pct_change()
    short_vol = ret.rolling(short_window).std().iloc[-1]
    long_vol = ret.rolling(long_window).std().iloc[-1]
    return (short_vol / long_vol) - 1.0
