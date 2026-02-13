"""Risk endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import RiskResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["risk"])


@router.get("/risk", response_model=RiskResponse)
def get_risk(
    service: DashboardDataService = Depends(get_data_service),
) -> RiskResponse:
    """Return risk analytics JSON payload."""
    return RiskResponse(**service.get_payload()["risk"])
