"""Optimization endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from dashboard.backend.schemas.api import OptimizationResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.backend.dependencies import get_data_service

router = APIRouter(tags=["optimization"])


@router.get("/optimization", response_model=OptimizationResponse)
def get_optimization(
    service: DashboardDataService = Depends(get_data_service),
) -> OptimizationResponse:
    """Return optimization JSON payload."""
    return OptimizationResponse(**service.get_payload()["optimization"])
