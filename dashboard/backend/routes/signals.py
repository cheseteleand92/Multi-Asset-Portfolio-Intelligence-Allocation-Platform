"""Signal endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import SignalsResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
def get_signals(
    service: DashboardDataService = Depends(get_data_service),
) -> SignalsResponse:
    """Return signals/regime JSON payload."""
    return SignalsResponse(**service.get_payload()["signals"])
