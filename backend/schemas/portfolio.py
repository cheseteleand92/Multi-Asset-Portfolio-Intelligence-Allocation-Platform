from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    description: str = ""


class PortfolioRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    ticker: str
    asset_class: str = "Equity"
    quantity: float
    cost_price: float
    currency: str = "USD"


class PositionRead(PositionCreate):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}
