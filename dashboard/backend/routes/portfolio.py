"""Portfolio endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import PortfolioResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["portfolio"])
service = DashboardDataService()


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio() -> PortfolioResponse:
    """Return portfolio overview JSON payload."""
    return PortfolioResponse(**service.get_payload()["portfolio"])
