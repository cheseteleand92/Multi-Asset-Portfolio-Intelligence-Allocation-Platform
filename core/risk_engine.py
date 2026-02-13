"""Risk analytics including VaR, ES, and contribution decomposition."""
from __future__ import annotations

import numpy as np
import pandas as pd


def portfolio_volatility(weights: pd.Series, cov: pd.DataFrame) -> float:
    """Compute annualized volatility from covariance matrix."""
    w = weights.values
    sigma = cov.loc[weights.index, weights.index].values
    return float(np.sqrt(w.T @ sigma @ w))


def marginal_risk_contribution(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Compute marginal contribution to volatility: (Σw)_i / σ_p."""
    w = weights.values
    sigma = cov.loc[weights.index, weights.index].values
    port_vol = np.sqrt(w.T @ sigma @ w)
    mrc = (sigma @ w) / port_vol
    return pd.Series(mrc, index=weights.index)


def total_risk_contribution(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Compute total contribution to volatility: w_i * MRC_i."""
    return weights * marginal_risk_contribution(weights, cov)


def historical_var(returns: pd.Series, alpha: float = 0.95) -> float:
    """Historical Value-at-Risk at confidence level alpha."""
    return float(np.quantile(-returns.dropna(), alpha))


def historical_es(returns: pd.Series, alpha: float = 0.95) -> float:
    """Historical Expected Shortfall at confidence level alpha."""
    losses = -returns.dropna()
    var = np.quantile(losses, alpha)
    tail = losses[losses >= var]
    return float(tail.mean()) if len(tail) else float(var)
