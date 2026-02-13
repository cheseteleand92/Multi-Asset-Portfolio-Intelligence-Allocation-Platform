"""Optimization endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from dashboard.backend.schemas.api import OptimizationResponse
from dashboard.backend.services.data_service import DashboardDataService

router = APIRouter(tags=["optimization"])
service = DashboardDataService()


@router.get("/optimization", response_model=OptimizationResponse)
def get_optimization() -> OptimizationResponse:
    """Return optimization JSON payload."""
    return OptimizationResponse(**service.get_payload()["optimization"])
