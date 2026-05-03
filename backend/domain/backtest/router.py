from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.domain.backtest import service
from backend.domain.backtest.models import BacktestResult as BacktestResultORM
from backend.domain.backtest.models import BacktestRun

router = APIRouter(tags=["backtest"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/backtests/strategies")
def list_strategies():
    return service.get_strategies()


@router.get("/backtests/benchmarks")
def list_benchmarks():
    return service.get_benchmarks()


@router.post("/backtests", status_code=201)
def create_backtest(body: dict[str, Any], db: DbSession):
    portfolio_id = body.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id required")
    try:
        run = service.run_backtest(db, portfolio_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"run_id": run.id, "strategy": run.strategy}


@router.post("/backtests/sweep")
def sweep_backtests(body: dict[str, Any], db: DbSession):
    portfolio_id = body.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id required")
    try:
        runs = service.run_backtest_sweep(db, portfolio_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"count": len(runs), "runs": runs}


@router.get("/backtests/{run_id}")
def get_backtest(run_id: int, db: DbSession):
    run = db.get(BacktestRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    params = json.loads(run.params_json)
    results = (
        db.query(BacktestResultORM)
        .filter_by(run_id=run_id)
        .order_by(BacktestResultORM.date)
        .all()
    )
    benchmark_result = service.build_benchmark_result(db, run.portfolio_id, params)
    metrics = []
    for result in results:
        payload = json.loads(result.metrics_json or "{}")
        metrics.append({
            "date": result.date.isoformat(),
            "turnover": payload.get("turnover", 0.0),
            "transaction_cost": payload.get("transaction_cost", 0.0),
        })
    return {
        "run_id": run.id,
        "strategy": run.strategy,
        "params": params,
        "nav": [{"date": r.date.isoformat(), "nav": r.nav} for r in results],
        "metrics": metrics,
        "benchmark": (
            []
            if benchmark_result is None
            else [
                {"date": dt.date().isoformat(), "nav": float(nav)}
                for dt, nav in benchmark_result.nav.items()
            ]
        ),
        "relative_attribution": service.build_relative_attribution(results, benchmark_result),
    }


@router.get("/portfolios/{portfolio_id}/backtests")
def list_backtests(portfolio_id: int, db: DbSession):
    runs = db.query(BacktestRun).filter_by(portfolio_id=portfolio_id).all()
    return [
        {"run_id": r.id, "strategy": r.strategy, "created_at": r.created_at.isoformat()}
        for r in runs
    ]


@router.get("/portfolios/{portfolio_id}/backtests/precheck")
def precheck_backtest(portfolio_id: int, lookback_days: int = 63, *, db: DbSession):
    return service.backtest_precheck(db, portfolio_id, lookback_days=lookback_days)
