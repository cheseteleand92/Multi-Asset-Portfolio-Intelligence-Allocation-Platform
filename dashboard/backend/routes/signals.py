"""Signal endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import SignalsResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["signals"])
service = DashboardDataService()


@router.get("/signals", response_model=SignalsResponse)
def get_signals() -> SignalsResponse:
    """Return signals/regime JSON payload."""
    return SignalsResponse(**service.get_payload()["signals"])
