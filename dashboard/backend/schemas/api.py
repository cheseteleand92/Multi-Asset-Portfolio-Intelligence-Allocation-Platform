"""Pydantic response schemas for dashboard API endpoints."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class PortfolioResponse(BaseModel):
    """Portfolio overview payload."""

    nav: List[float]
    allocation: Dict[str, float]
    rolling_return: List[float]
    risk_contribution: Dict[str, float]


class RiskResponse(BaseModel):
    """Risk analytics payload."""

    correlation_matrix: Dict[str, Dict[str, float]]
    beta_exposure: Dict[str, float]
    duration_exposure: Dict[str, float]
    tracking_error: float


class FactorResponse(BaseModel):
    """Factor model payload."""

    factor_exposure: Dict[str, float]
    factor_risk_contribution: Dict[str, float]
    factor_covariance: Dict[str, Dict[str, float]]
    factor_share: float
    specific_share: float


class OptimizationResponse(BaseModel):
    """Optimization diagnostics payload."""

    efficient_frontier_risk: List[float]
    efficient_frontier_return: List[float]
    weight_comparison: Dict[str, float]
    risk_budget_allocation: Dict[str, float]
    constraint_impact: Dict[str, float]


class MacroResponse(BaseModel):
    """Macro intelligence payload."""

    yield_curve: List[float]
    credit_spread: List[float]
    fx_index: List[float]
    volatility_index: List[float]
    scenario_shock_result: Dict[str, float]


class SignalsResponse(BaseModel):
    """Regime and tactical signals payload."""

    regime_probability: List[float]
    signals: Dict[str, float]
    suggested_allocation_shift: Dict[str, float]


class DashboardBundleResponse(BaseModel):
    """Combined response for frontend bootstrap."""

    portfolio: PortfolioResponse
    risk: RiskResponse
    factor: FactorResponse
    optimization: OptimizationResponse
    macro: MacroResponse
    signals: SignalsResponse
    timestamp: str = Field(description="ISO8601 payload generation timestamp")
