"""Backend data service to assemble dashboard endpoint payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

import numpy as np
import pandas as pd

from core.factor_model import FactorModel


class DashboardDataService:
    """Generate dashboard payloads (placeholder for DB + Bloomberg integrated service)."""

    def __init__(self) -> None:
        self.assets = ["US Equity", "Japan Equity", "China A", "Gov Bonds", "Credit", "FX", "Commodities"]
        self.factors = [
            "Value",
            "Momentum",
            "Growth",
            "Size",
            "LowVol",
            "Quality",
            "YieldSlope",
            "RealRate",
            "InflationSurprise",
            "CreditSpread",
            "USDStrength",
            "VIX",
            "EquityBeta",
            "Duration",
            "FXBeta",
            "CommodityBeta",
        ]

    def _synthetic_factor_block(self) -> Dict[str, object]:
        np.random.seed(1)
        dates = pd.bdate_range("2024-01-01", periods=320)
        asset_rets = pd.DataFrame(np.random.normal(0.0002, 0.01, (len(dates), len(self.assets))), index=dates, columns=self.assets)
        factor_rets = pd.DataFrame(np.random.normal(0.0, 0.008, (len(dates), len(self.factors))), index=dates, columns=self.factors)

        fm = FactorModel(window=252, shrinkage=True)
        result = fm.fit(asset_rets, factor_rets)

        weights = pd.Series([0.30, 0.12, 0.10, 0.23, 0.10, 0.05, 0.10], index=self.assets)
        decomp = fm.portfolio_risk_decomposition(weights, result.exposures, result.factor_cov, result.specific_var)

        factor_port_exposure = (result.exposures.loc[self.assets, self.factors].T @ weights).to_dict()
        factor_risk = (result.exposures.loc[self.assets, self.factors].T @ weights).abs()
        factor_risk = (factor_risk / factor_risk.sum()).to_dict()

        corr = asset_rets.corr().round(3).to_dict()
        return {
            "factor_exposure": {k: float(v) for k, v in factor_port_exposure.items()},
            "factor_risk_contribution": {k: float(v) for k, v in factor_risk.items()},
            "factor_covariance": result.factor_cov.round(6).to_dict(),
            "factor_share": float(decomp["factor_share"]),
            "specific_share": float(decomp["specific_share"]),
            "correlation": corr,
        }

    def get_payload(self) -> Dict[str, object]:
        """Return complete dashboard bundle payload."""
        factor_block = self._synthetic_factor_block()

        payload = {
            "portfolio": {
                "nav": [100, 101.5, 103.0, 102.2, 104.1, 105.3, 106.0],
                "allocation": {"US Equity": 0.30, "Japan Equity": 0.12, "China A": 0.10, "Gov Bonds": 0.23, "Credit": 0.10, "FX": 0.05, "Commodities": 0.10},
                "rolling_return": [0.010, 0.012, 0.011, 0.015, 0.014, 0.013],
                "risk_contribution": {"US Equity": 0.28, "Japan Equity": 0.10, "China A": 0.09, "Gov Bonds": 0.21, "Credit": 0.13, "FX": 0.07, "Commodities": 0.12},
            },
            "risk": {
                "correlation_matrix": factor_block["correlation"],
                "beta_exposure": {"Portfolio Beta": 0.94, "Benchmark Beta": 1.0},
                "duration_exposure": {"Portfolio Duration": 4.8, "Benchmark Duration": 5.0},
                "tracking_error": 0.034,
            },
            "factor": {
                "factor_exposure": factor_block["factor_exposure"],
                "factor_risk_contribution": factor_block["factor_risk_contribution"],
                "factor_covariance": factor_block["factor_covariance"],
                "factor_share": factor_block["factor_share"],
                "specific_share": factor_block["specific_share"],
            },
            "optimization": {
                "efficient_frontier_risk": [0.06, 0.08, 0.10, 0.12, 0.15],
                "efficient_frontier_return": [0.04, 0.055, 0.066, 0.074, 0.083],
                "weight_comparison": {"US Equity": -0.02, "Japan Equity": 0.01, "China A": 0.02, "Gov Bonds": -0.01, "Credit": 0.0, "FX": 0.0, "Commodities": 0.0},
                "risk_budget_allocation": {"US Equity": 0.20, "Japan Equity": 0.11, "China A": 0.09, "Gov Bonds": 0.28, "Credit": 0.14, "FX": 0.06, "Commodities": 0.12},
                "constraint_impact": {"vol_target": 0.12, "te_constraint": 0.035, "regional_cap_asia": 0.25, "turnover_penalty": 0.005},
            },
            "macro": {
                "yield_curve": [2.1, 2.3, 2.55, 2.72, 2.88],
                "credit_spread": [1.45, 1.43, 1.49, 1.54, 1.5],
                "fx_index": [100.1, 99.9, 100.4, 101.0, 100.7],
                "volatility_index": [18.5, 17.8, 19.1, 20.0, 18.9],
                "scenario_shock_result": {"rate_shock": -0.024, "equity_crash": -0.088, "fx_shock": -0.015},
            },
            "signals": {
                "regime_probability": [0.35, 0.40, 0.52, 0.61, 0.58, 0.64],
                "signals": {"Momentum": 0.62, "Carry": 0.48, "YieldCurve": -0.23, "RiskOn": 0.56},
                "suggested_allocation_shift": {"US Equity": 0.01, "Japan Equity": 0.01, "Gov Bonds": -0.01, "FX": -0.01},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return payload
