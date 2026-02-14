from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.backtest import service
from backend.domain.backtest.models import BacktestRun
from backend.domain.backtest.models import BacktestResult as BacktestResultORM

router = APIRouter(tags=["backtest"])


@router.get("/backtests/strategies")
def list_strategies():
    return service.get_strategies()


@router.get("/backtests/benchmarks")
def list_benchmarks():
    return service.get_benchmarks()


@router.post("/backtests", status_code=201)
def create_backtest(body: dict, db: Session = Depends(get_db)):
    portfolio_id = body.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id required")
    try:
        run = service.run_backtest(db, portfolio_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"run_id": run.id, "strategy": run.strategy}


@router.get("/backtests/{run_id}")
def get_backtest(run_id: int, db: Session = Depends(get_db)):
    run = db.get(BacktestRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    params = json.loads(run.params_json)
    results = (db.query(BacktestResultORM)
               .filter_by(run_id=run_id)
               .order_by(BacktestResultORM.date)
               .all())
    return {
        "run_id": run.id,
        "strategy": run.strategy,
        "params": params,
        "nav": [{"date": r.date.isoformat(), "nav": r.nav} for r in results],
        "benchmark": service.build_benchmark_nav(db, run.portfolio_id, params),
    }


@router.get("/portfolios/{portfolio_id}/backtests")
def list_backtests(portfolio_id: int, db: Session = Depends(get_db)):
    runs = db.query(BacktestRun).filter_by(portfolio_id=portfolio_id).all()
    return [
        {"run_id": r.id, "strategy": r.strategy, "created_at": r.created_at.isoformat()}
        for r in runs
    ]
