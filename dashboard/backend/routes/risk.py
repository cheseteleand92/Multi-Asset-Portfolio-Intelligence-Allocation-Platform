"""Risk endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import RiskResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["risk"])
service = DashboardDataService()


@router.get("/risk", response_model=RiskResponse)
def get_risk() -> RiskResponse:
    """Return risk analytics JSON payload."""
    return RiskResponse(**service.get_payload()["risk"])
