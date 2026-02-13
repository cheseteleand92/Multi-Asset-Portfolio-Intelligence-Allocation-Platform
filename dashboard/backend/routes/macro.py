"""Macro intelligence endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import MacroResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["macro"])
service = DashboardDataService()


@router.get("/macro", response_model=MacroResponse)
def get_macro() -> MacroResponse:
    """Return macro JSON payload."""
    return MacroResponse(**service.get_payload()["macro"])
