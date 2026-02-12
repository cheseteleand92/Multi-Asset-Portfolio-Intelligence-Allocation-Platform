"""Performance metrics for backtests."""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_sharpe(returns: pd.Series, window: int = 126) -> pd.Series:
    """Annualized rolling Sharpe ratio."""
    mean = returns.rolling(window).mean() * 252
    vol = returns.rolling(window).std() * np.sqrt(252)
    return mean / vol


def drawdown(nav: pd.Series) -> pd.Series:
    """Compute drawdown series."""
    peak = nav.cummax()
    return nav / peak - 1
