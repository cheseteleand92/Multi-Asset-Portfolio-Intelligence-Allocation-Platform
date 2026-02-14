from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.analytics import service
from backend.domain.analytics.stress import SCENARIOS, run_scenario
from backend.domain.market_data.service import (
    position_values_base,
    positions_to_base_returns,
)
from backend.domain.portfolio.service import get_positions

router = APIRouter(tags=["analytics"])


def _portfolio_data(portfolio_id: int, db: Session, base_currency: str = "USD"):
    positions = get_positions(db, portfolio_id)
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found")

    base = base_currency.upper()
    returns, fx_warnings, fx_used = positions_to_base_returns(db, positions, base_currency=base)
    values_base, value_warnings, _ = position_values_base(db, positions, base_currency=base)

    weights: dict[str, float] = {}
    total_value = sum(values_base.values())
    if total_value > 0:
        weights = {t: v / total_value for t, v in values_base.items() if t in returns.columns}

    meta = {
        "base_currency": base,
        "fx_warnings": fx_warnings + value_warnings,
        "fx_used": fx_used,
        "position_values_base": values_base,
    }
    return weights, returns, meta


def _monitoring_config(
    lookback_days: int,
    return_frequency: str,
    confidence_level: float,
    annualization: int | None,
    risk_free_rate: float,
    as_of_date: date | None,
) -> dict:
    return {
        "lookback_days": lookback_days,
        "return_frequency": return_frequency,
        "confidence_level": confidence_level,
        "annualization": annualization,
        "risk_free_rate": risk_free_rate,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
    }


@router.get("/portfolios/{portfolio_id}/analytics")
def get_analytics(
    portfolio_id: int,
    lookback_days: int = Query(252, ge=21, le=5000),
    return_frequency: str = Query("daily"),
    annualization: int | None = Query(None, ge=1, le=5000),
    risk_free_rate: float = Query(0.0),
    base_currency: str = Query("USD", min_length=3, max_length=3),
    as_of_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    weights, returns, meta = _portfolio_data(portfolio_id, db, base_currency=base_currency)
    config = _monitoring_config(
        lookback_days=lookback_days,
        return_frequency=return_frequency,
        confidence_level=0.95,
        annualization=annualization,
        risk_free_rate=risk_free_rate,
        as_of_date=as_of_date,
    )
    out = service.compute_nav(returns, weights, config=config)
    warnings = out.get("warnings", [])
    out["warnings"] = [*warnings, *meta["fx_warnings"]]
    out["weights"] = weights
    out["base_currency"] = meta["base_currency"]
    out["fx_used"] = meta["fx_used"]
    out["position_values_base"] = meta["position_values_base"]
    return out


@router.get("/portfolios/{portfolio_id}/risk")
def get_risk(
    portfolio_id: int,
    lookback_days: int = Query(252, ge=21, le=5000),
    return_frequency: str = Query("daily"),
    confidence_level: float = Query(0.95, ge=0.80, le=0.995),
    annualization: int | None = Query(None, ge=1, le=5000),
    risk_free_rate: float = Query(0.0),
    base_currency: str = Query("USD", min_length=3, max_length=3),
    as_of_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    weights, returns, meta = _portfolio_data(portfolio_id, db, base_currency=base_currency)
    config = _monitoring_config(
        lookback_days=lookback_days,
        return_frequency=return_frequency,
        confidence_level=confidence_level,
        annualization=annualization,
        risk_free_rate=risk_free_rate,
        as_of_date=as_of_date,
    )
    out = service.compute_risk(returns, weights, config=config)
    warnings = out.get("warnings", [])
    out["warnings"] = [*warnings, *meta["fx_warnings"]]
    out["base_currency"] = meta["base_currency"]
    out["fx_used"] = meta["fx_used"]
    return out


@router.post("/portfolios/{portfolio_id}/what-if")
def what_if(portfolio_id: int, body: dict, db: Session = Depends(get_db)):
    adjusted_weights: dict = body.get("adjusted_weights", {})
    _, returns, _ = _portfolio_data(portfolio_id, db, base_currency="USD")
    return service.compute_risk(returns, adjusted_weights)


@router.get("/stress-test/scenarios")
def list_scenarios():
    return [{"id": k, "description": v["description"]} for k, v in SCENARIOS.items()]


@router.post("/portfolios/{portfolio_id}/stress-test")
def stress_test(portfolio_id: int, body: dict, db: Session = Depends(get_db)):
    scenario_id = body.get("scenario_id")
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    positions = get_positions(db, portfolio_id)
    if not positions:
        raise HTTPException(status_code=404, detail="No positions")
    scenario = {k: v for k, v in SCENARIOS[scenario_id].items() if k != "description"}
    return run_scenario(positions, scenario)
