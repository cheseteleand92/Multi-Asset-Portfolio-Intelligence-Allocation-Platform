from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.analytics import service
from backend.domain.analytics.stress import SCENARIOS, run_scenario
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions

router = APIRouter(tags=["analytics"])


def _portfolio_data(portfolio_id: int, db: Session):
    positions = get_positions(db, portfolio_id)
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found")
    tickers = [p.ticker for p in positions]
    total_value = sum(p.quantity * p.cost_price for p in positions)
    weights = {p.ticker: (p.quantity * p.cost_price) / total_value for p in positions}
    returns = prices_to_returns(db, tickers)
    return weights, returns


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
    as_of_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    weights, returns = _portfolio_data(portfolio_id, db)
    config = _monitoring_config(
        lookback_days=lookback_days,
        return_frequency=return_frequency,
        confidence_level=0.95,
        annualization=annualization,
        risk_free_rate=risk_free_rate,
        as_of_date=as_of_date,
    )
    return {**service.compute_nav(returns, weights, config=config), "weights": weights}


@router.get("/portfolios/{portfolio_id}/risk")
def get_risk(
    portfolio_id: int,
    lookback_days: int = Query(252, ge=21, le=5000),
    return_frequency: str = Query("daily"),
    confidence_level: float = Query(0.95, ge=0.80, le=0.995),
    annualization: int | None = Query(None, ge=1, le=5000),
    risk_free_rate: float = Query(0.0),
    as_of_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    weights, returns = _portfolio_data(portfolio_id, db)
    config = _monitoring_config(
        lookback_days=lookback_days,
        return_frequency=return_frequency,
        confidence_level=confidence_level,
        annualization=annualization,
        risk_free_rate=risk_free_rate,
        as_of_date=as_of_date,
    )
    return service.compute_risk(returns, weights, config=config)


@router.post("/portfolios/{portfolio_id}/what-if")
def what_if(portfolio_id: int, body: dict, db: Session = Depends(get_db)):
    adjusted_weights: dict = body.get("adjusted_weights", {})
    _, returns = _portfolio_data(portfolio_id, db)
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
