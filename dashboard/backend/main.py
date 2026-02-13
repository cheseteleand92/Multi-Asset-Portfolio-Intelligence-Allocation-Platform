"""FastAPI backend with modular routes and embedded institutional Dash frontend."""
from __future__ import annotations

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from dashboard.backend.routes.factor import router as factor_router
from dashboard.backend.routes.macro import router as macro_router
from dashboard.backend.routes.optimization import router as optimization_router
from dashboard.backend.routes.portfolio import router as portfolio_router
from dashboard.backend.routes.risk import router as risk_router
from dashboard.backend.routes.signals import router as signals_router
from dashboard.backend.schemas.api import DashboardBundleResponse
from dashboard.backend.services.data_service import DashboardDataService
from dashboard.frontend.app import create_dashboard_app

app = FastAPI(title="Multi-Asset Portfolio Intelligence API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from dashboard.backend.dependencies import get_data_service

# Initialize service singleton for app startup
service = get_data_service()

app.include_router(portfolio_router)
app.include_router(risk_router)
app.include_router(factor_router)
app.include_router(optimization_router)
app.include_router(macro_router)
app.include_router(signals_router)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardBundleResponse)
def dashboard_bundle(
    service: DashboardDataService = Depends(get_data_service),
) -> DashboardBundleResponse:
    """Combined payload endpoint used by dashboard frontend bootstrap."""
    return DashboardBundleResponse(**service.get_payload())


# Mount Dash app with initial payload from the singleton service
_dash = create_dashboard_app(service.get_payload())
app.mount("/dashboard", WSGIMiddleware(_dash.server))
