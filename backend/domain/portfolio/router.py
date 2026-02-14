from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.portfolio import service
from backend.schemas.portfolio import (
    PortfolioCreate,
    PortfolioRead,
    PositionCreate,
    PositionRead,
    PositionUpdate,
)

router = APIRouter(tags=["portfolio"])


@router.get("/portfolios", response_model=list[PortfolioRead])
def list_portfolios(db: Session = Depends(get_db)):
    return service.list_portfolios(db)


@router.post("/portfolios", response_model=PortfolioRead, status_code=201)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    return service.create_portfolio(db, data)


@router.get("/portfolios/{portfolio_id}/positions", response_model=list[PositionRead])
def get_positions(portfolio_id: int, db: Session = Depends(get_db)):
    return service.get_positions(db, portfolio_id)


@router.post("/portfolios/{portfolio_id}/positions", response_model=PositionRead, status_code=201)
def add_position(portfolio_id: int, data: PositionCreate, db: Session = Depends(get_db)):
    return service.add_position(db, portfolio_id, data)


@router.delete("/positions/{position_id}", status_code=204)
def delete_position(position_id: int, db: Session = Depends(get_db)):
    service.delete_position(db, position_id)


@router.put("/positions/{position_id}", response_model=PositionRead)
def update_position(position_id: int, data: PositionUpdate, db: Session = Depends(get_db)):
    updated = service.update_position(db, position_id, data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Position not found")
    return updated


@router.post("/portfolios/{portfolio_id}/import-csv")
async def import_csv(
    portfolio_id: int,
    file: UploadFile,
    replace: bool = Query(False),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        count = service.import_csv(db, portfolio_id, content, replace=replace)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"imported": count}
