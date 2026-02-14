from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/portfolios/{portfolio_id}/analytics")
def get_analytics(portfolio_id: int, db: Session = Depends(get_db)):
    weights, returns = _portfolio_data(portfolio_id, db)
    return {**service.compute_nav(returns, weights), "weights": weights}


@router.get("/portfolios/{portfolio_id}/risk")
def get_risk(portfolio_id: int, db: Session = Depends(get_db)):
    weights, returns = _portfolio_data(portfolio_id, db)
    return service.compute_risk(returns, weights)


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
