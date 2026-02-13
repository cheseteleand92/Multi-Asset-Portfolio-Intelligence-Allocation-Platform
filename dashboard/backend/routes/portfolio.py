"""Portfolio endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import PortfolioResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(
    service: DashboardDataService = Depends(get_data_service),
) -> PortfolioResponse:
    """Return portfolio overview JSON payload."""
    return PortfolioResponse(**service.get_payload()["portfolio"])
