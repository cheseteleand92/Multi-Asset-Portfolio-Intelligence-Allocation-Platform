"""Risk analytics including VaR, ES, and contribution decomposition."""
from __future__ import annotations

import numpy as np
import pandas as pd



def portfolio_volatility(weights: pd.Series, cov: pd.DataFrame, annualization: int = 252) -> float:
    """Compute annualized volatility from covariance matrix.

    Args:
        weights: Portfolio weights.
        cov: Asset covariance matrix (assumed simple period, e.g., daily).
        annualization: Annualization factor (e.g., 252 for daily).
    """
    w = weights.values
    sigma = cov.loc[weights.index, weights.index].values
    vol = np.sqrt(w.T @ sigma @ w)
    return float(vol * np.sqrt(annualization))


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


def parametric_var(weights: pd.Series, cov: pd.DataFrame, alpha: float = 0.95, z_score: float = None) -> float:
    """Parametric (Gaussian) Value-at-Risk."""
    from scipy.stats import norm
    
    if z_score is None:
        z_score = norm.ppf(alpha)
        
    vol = portfolio_volatility(weights, cov, annualization=1)  # Daily vol
    return float(z_score * vol)


def max_drawdown(returns: pd.Series) -> float:
    """Compute maximum drawdown from return series."""
    nav = (1 + returns).cumprod()
    peak = nav.expanding(min_periods=1).max()
    dd = (nav - peak) / peak
    return float(dd.min())


def sortino_ratio(returns: pd.Series, target_return: float = 0.0, annualization: int = 252) -> float:
    """Compute Sortino Ratio (return / downside deviation)."""
    excess_return = returns - target_return / annualization
    downside_returns = excess_return[excess_return < 0]
    downside_dev = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(annualization)
    
    mean_ret = returns.mean() * annualization
    if np.isclose(downside_dev, 0.0):
        return np.inf if mean_ret > 0 else -np.inf
    return float((mean_ret - target_return) / downside_dev)


def calmar_ratio(returns: pd.Series, annualization: int = 252) -> float:
    """Compute Calmar Ratio (annualized return / max drawdown)."""
    mdd = abs(max_drawdown(returns))
    if np.isclose(mdd, 0.0):
        return np.inf
    cagr = (1 + returns).prod() ** (annualization / len(returns)) - 1
    return float(cagr / mdd)


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series, annualization: int = 252) -> float:
    """Compute Information Ratio (active return / tracking error)."""
    active_ret = returns - benchmark_returns
    tracking_error = active_ret.std() * np.sqrt(annualization)
    if np.isclose(tracking_error, 0.0):
        return 0.0
    return float((active_ret.mean() * annualization) / tracking_error)
