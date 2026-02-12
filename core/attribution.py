"""Performance attribution methods."""
from __future__ import annotations

import pandas as pd


def brinson_attribution(
    portfolio_weights: pd.Series,
    benchmark_weights: pd.Series,
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> pd.DataFrame:
    """Single-period Brinson attribution decomposition."""
    df = pd.concat(
        [portfolio_weights, benchmark_weights, portfolio_returns, benchmark_returns], axis=1
    ).fillna(0.0)
    df.columns = ["wp", "wb", "rp", "rb"]
    df["allocation"] = (df["wp"] - df["wb"]) * df["rb"]
    df["selection"] = df["wb"] * (df["rp"] - df["rb"])
    df["interaction"] = (df["wp"] - df["wb"]) * (df["rp"] - df["rb"])
    return df
