"""FastAPI backend serving portfolio intelligence endpoints and embedded Dash UI."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from dashboard.frontend.app import create_dashboard_app

app = FastAPI(title="Multi-Asset Portfolio Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sample_payload() -> Dict[str, Any]:
    """Institutional dashboard payload placeholder for local development."""
    return {
        "overview": {
            "nav": [100, 101, 102, 103, 102.5, 104.2],
            "allocation": {"US Equity": 0.30, "Japan Equity": 0.12, "China A": 0.10, "Gov Bonds": 0.28, "Credit": 0.10, "Commodities": 0.10},
            "pnl_breakdown": {"Equity": 1.2, "Rates": 0.4, "FX": -0.2, "Commodities": 0.6},
            "rolling_return": [0.01, 0.015, 0.013, 0.02, 0.018],
        },
        "risk_factor": {
            "factor_exposure": {
                "Value": 0.25,
                "Momentum": 0.18,
                "Growth": 0.09,
                "Size": -0.05,
                "LowVol": 0.21,
                "Quality": 0.17,
                "YieldSlope": -0.12,
                "CreditSpread": 0.08,
                "USD": 0.11,
            },
            "factor_risk_contribution": {"Value": 0.14, "Momentum": 0.16, "Rates": 0.22, "Credit": 0.18, "FX": 0.11, "Commodity": 0.19},
            "beta_exposure": {"Portfolio Beta": 0.92, "Benchmark Beta": 1.00},
            "duration_exposure": {"Portfolio Duration": 4.7, "Benchmark Duration": 5.1},
        },
        "optimization": {
            "efficient_frontier": [0.035, 0.05, 0.062, 0.07, 0.078],
            "risk_budget_allocation": {"US Equity": 0.20, "Japan Equity": 0.10, "China A": 0.10, "Gov Bonds": 0.30, "Credit": 0.15, "FX": 0.05, "Commodities": 0.10},
            "weight_comparison": {"US Equity": -0.02, "Japan Equity": 0.01, "China A": 0.02, "Gov Bonds": -0.01, "Credit": 0.00, "FX": 0.01, "Commodities": -0.01},
        },
        "regime_taa": {
            "regime_probability": [0.35, 0.41, 0.55, 0.62, 0.58, 0.65],
            "signals": {"Momentum": 0.62, "Carry": 0.47, "YieldCurve": -0.23, "RiskOn": 0.55},
            "suggested_shift": {"US Equity": 0.01, "Japan Equity": 0.01, "Gov Bonds": -0.01, "FX": -0.01},
        },
        "macro": {
            "yield_curve": [2.1, 2.4, 2.55, 2.7, 2.85],
            "fx_dashboard": [143.2, 142.8, 141.9, 142.3, 141.4],
            "credit_spread": [1.45, 1.42, 1.48, 1.53, 1.49],
            "volatility_index": [18.5, 17.9, 19.3, 20.1, 18.8],
        },
    }


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard_payload() -> Dict[str, Any]:
    """Return full dashboard payload for all panels."""
    return _sample_payload()


_dash = create_dashboard_app(_sample_payload())
app.mount("/dashboard", WSGIMiddleware(_dash.server))
