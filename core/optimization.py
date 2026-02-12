"""Portfolio optimization toolkit."""
from __future__ import annotations

import cvxpy as cp
import numpy as np
import pandas as pd


def mean_variance_opt(
    exp_returns: pd.Series,
    cov: pd.DataFrame,
    risk_aversion: float = 5.0,
    long_only: bool = True,
    max_weight: float = 0.30,
) -> pd.Series:
    """Classic mean-variance optimization.

    maximize: mu'w - lambda * w'Σw
    """
    names = exp_returns.index
    mu = exp_returns.values
    sigma = cov.loc[names, names].values
    w = cp.Variable(len(names))
    objective = cp.Maximize(mu @ w - risk_aversion * cp.quad_form(w, sigma))
    cons = [cp.sum(w) == 1, w <= max_weight]
    if long_only:
        cons.append(w >= 0)
    cp.Problem(objective, cons).solve(solver=cp.SCS)
    return pd.Series(np.array(w.value).flatten(), index=names)


def black_litterman_posterior(
    cov: pd.DataFrame,
    market_weights: pd.Series,
    delta: float,
    p: np.ndarray,
    q: np.ndarray,
    omega: np.ndarray,
    tau: float = 0.05,
) -> pd.Series:
    """Return Black-Litterman posterior expected returns."""
    sigma = cov.loc[market_weights.index, market_weights.index].values
    pi = delta * sigma @ market_weights.values
    ts = tau * sigma
    m = np.linalg.inv(np.linalg.inv(ts) + p.T @ np.linalg.inv(omega) @ p)
    adj = np.linalg.inv(ts) @ pi + p.T @ np.linalg.inv(omega) @ q
    posterior = m @ adj
    return pd.Series(posterior, index=market_weights.index)
