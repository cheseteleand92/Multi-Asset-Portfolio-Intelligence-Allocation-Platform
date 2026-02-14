"""FastAPI application entry point."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables
from backend.domain.portfolio.router import router as portfolio_router
from backend.domain.market_data.router import router as market_data_router
from backend.domain.analytics.router import router as analytics_router
from backend.domain.signals.router import router as signals_router
from backend.domain.backtest.router import router as backtest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Portfolio Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router, prefix="/api")
app.include_router(market_data_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(backtest_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
