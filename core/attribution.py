"""Performance attribution methods."""
from __future__ import annotations

import numpy as np
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


def multi_period_attribution(
    single_period_results: list[pd.DataFrame],
    linking_method: str = "carino",
) -> pd.DataFrame:
    """Link single-period attribution results over time.

    Uses Carino smoothing coefficients to link arithmetic attribution
    to geometric cumulative returns.
    """
    if not single_period_results:
        return pd.DataFrame()

    # We need portfolio level totals for each period
    period_data = []
    for df in single_period_results:
        R_p = (df["wp"] * df["rp"]).sum()
        R_b = (df["wb"] * df["rb"]).sum()
        period_data.append({"Rp": R_p, "Rb": R_b, "df": df})

    total_Rp = (1 + pd.Series([p["Rp"] for p in period_data])).prod() - 1
    total_Rb = (1 + pd.Series([p["Rb"] for p in period_data])).prod() - 1

    # Carino smoothing
    # k_t = log(1 + R_pt) / R_pt  (if R_pt small approx 1)
    # But usually k_t = (ln(1+Rp) - ln(1+Rb)) / (Rp - Rb)
    if abs(total_Rp - total_Rb) > 1e-6:
        k_total = (np.log(1 + total_Rp) - np.log(1 + total_Rb)) / (total_Rp - total_Rb)
    else:
        k_total = 1.0

    aggregated = pd.DataFrame(
        0.0,
        index=single_period_results[0].index,
        columns=["allocation", "selection", "interaction"],
    )

    for p in period_data:
        rp = p["Rp"]
        rb = p["Rb"]
        kt = (np.log(1 + rp) - np.log(1 + rb)) / (rp - rb) if abs(rp - rb) > 1e-6 else 1.0

        # Attribution for this period
        attr = p["df"][["allocation", "selection", "interaction"]]

        # Link
        # Contribution = attr * kt / k_total ??
        # Carino: C_i = sum(C_it * k_t) / k_total

        aggregated += attr * kt

    return aggregated / k_total
