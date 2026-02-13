"""Macro intelligence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import MacroResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["macro"])


@router.get("/macro", response_model=MacroResponse)
def get_macro(
    service: DashboardDataService = Depends(get_data_service),
) -> MacroResponse:
    """Return macro JSON payload."""
    return MacroResponse(**service.get_payload()["macro"])
