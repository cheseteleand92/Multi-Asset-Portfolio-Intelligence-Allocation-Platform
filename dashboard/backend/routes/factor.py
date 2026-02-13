"""Factor endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import FactorResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["factor"])
service = DashboardDataService()


@router.get("/factor", response_model=FactorResponse)
def get_factor() -> FactorResponse:
    """Return factor model JSON payload."""
    return FactorResponse(**service.get_payload()["factor"])
