"""Factor endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import FactorResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["factor"])


@router.get("/factor", response_model=FactorResponse)
def get_factor(
    service: DashboardDataService = Depends(get_data_service),
) -> FactorResponse:
    """Return factor model JSON payload."""
    return FactorResponse(**service.get_payload()["factor"])
