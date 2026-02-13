"""Multi-factor risk model for cross-asset portfolios."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


@dataclass
class FactorModelResult:
    """Container for estimated factor model outputs."""

    exposures: pd.DataFrame
    factor_cov: pd.DataFrame
    specific_var: pd.Series


class FactorModel:
    """Estimate exposures and covariance for a linear factor model.

    Model assumption:
        r_t = B f_t + e_t
    where B is exposure matrix, f_t are factor returns, and e_t specific return.
    """

    def __init__(self, window: int = 252, shrinkage: bool = True) -> None:
        self.window = window
        self.shrinkage = shrinkage

    def estimate_exposures(
        self,
        asset_returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
        add_intercept: bool = True,
    ) -> pd.DataFrame:
        """Estimate rolling OLS exposures for each asset.

        Returns latest-window exposure estimates.
        """
        if len(asset_returns) < self.window or len(factor_returns) < self.window:
            raise ValueError("Not enough observations for configured rolling window.")

        joined = asset_returns.join(factor_returns, how="inner")
        joined = joined.iloc[-self.window :]
        x = joined[factor_returns.columns].copy()

        if add_intercept:
            x["intercept"] = 1.0

        x_mat = x.values
        xtx_inv = np.linalg.pinv(x_mat.T @ x_mat)
        betas: Dict[str, np.ndarray] = {}

        for asset in asset_returns.columns:
            y = joined[asset].values
            beta = xtx_inv @ x_mat.T @ y
            betas[asset] = beta

        exposures = pd.DataFrame(betas, index=x.columns).T
        return exposures

    def estimate_factor_covariance(self, factor_returns: pd.DataFrame) -> pd.DataFrame:
        """Estimate factor covariance with optional Ledoit-Wolf shrinkage."""
        data = factor_returns.iloc[-self.window :].dropna()
        if self.shrinkage:
            lw = LedoitWolf().fit(data.values)
            cov = pd.DataFrame(lw.covariance_, index=data.columns, columns=data.columns)
        else:
            cov = data.cov()
        return cov

    def estimate_specific_variance(
        self,
        asset_returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
        exposures: pd.DataFrame,
    ) -> pd.Series:
        """Estimate idiosyncratic variance for each asset."""
        common_idx = asset_returns.index.intersection(factor_returns.index)
        a = asset_returns.loc[common_idx]
        f = factor_returns.loc[common_idx, exposures.columns.intersection(factor_returns.columns)]
        residual_var = {}
        b = exposures[f.columns]

        for asset in a.columns.intersection(exposures.index):
            fitted = f.values @ b.loc[asset].values
            resid = a[asset].values - fitted
            residual_var[asset] = np.var(resid, ddof=1)

        return pd.Series(residual_var)

    def fit(self, asset_returns: pd.DataFrame, factor_returns: pd.DataFrame) -> FactorModelResult:
        """Fit full factor model and return exposures/covariance/specific risk."""
        exposures = self.estimate_exposures(asset_returns, factor_returns, add_intercept=False)
        factor_cov = self.estimate_factor_covariance(factor_returns)
        specific_var = self.estimate_specific_variance(asset_returns, factor_returns, exposures)
        return FactorModelResult(exposures=exposures, factor_cov=factor_cov, specific_var=specific_var)

    @staticmethod
    def portfolio_risk_decomposition(
        weights: pd.Series,
        exposures: pd.DataFrame,
        factor_cov: pd.DataFrame,
        specific_var: pd.Series,
    ) -> Dict[str, float]:
        """Decompose portfolio variance into factor and specific components.

        Formula:
            Var_p = w' B F B' w + w' D w
        where D is diagonal matrix of specific variances.
        """
        assets = weights.index.intersection(exposures.index).intersection(specific_var.index)
        w = weights.loc[assets].values
        b = exposures.loc[assets, factor_cov.index].values
        f = factor_cov.values
        d = np.diag(specific_var.loc[assets].values)

        factor_var = float(w.T @ b @ f @ b.T @ w)
        specific = float(w.T @ d @ w)
        total = factor_var + specific
        return {
            "factor_variance": factor_var,
            "specific_variance": specific,
            "total_variance": total,
            "factor_share": factor_var / total if total else np.nan,
            "specific_share": specific / total if total else np.nan,
        }

    @staticmethod
    def factor_risk_contribution(
        weights: pd.Series,
        exposures: pd.DataFrame,
        factor_cov: pd.DataFrame,
    ) -> pd.Series:
        """Compute normalized factor contribution to portfolio variance.

        For factor k contribution, this uses:
            c = (B'w) ⊙ (F (B'w))
        and returns c / sum(c).
        """
        assets = weights.index.intersection(exposures.index)
        factor_cols = factor_cov.index.intersection(exposures.columns)
        w = weights.loc[assets].values
        b = exposures.loc[assets, factor_cols].values
        f = factor_cov.loc[factor_cols, factor_cols].values
        factor_port = b.T @ w
        contrib = factor_port * (f @ factor_port)
        s = contrib.sum()
        return pd.Series(contrib / s if s else contrib, index=factor_cols)
