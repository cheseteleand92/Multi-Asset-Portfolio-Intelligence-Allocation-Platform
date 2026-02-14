from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.deps import get_db
from backend.domain.market_data.models import MarketData
from backend.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _seed_portfolio_and_prices(client: TestClient) -> int:
    pid = client.post("/api/portfolios", json={"name": "Risk API"}).json()["id"]
    tickers = ["AAPL US Equity", "MSFT US Equity", "GOOG US Equity"]
    for ticker in tickers:
        r = client.post(
            f"/api/portfolios/{pid}/positions",
            json={
                "ticker": ticker,
                "quantity": 100,
                "cost_price": 100.0,
                "currency": "USD",
                "asset_class": "Equity",
            },
        )
        assert r.status_code == 201

    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    with TestSession() as db:
        for idx, ticker in enumerate(tickers):
            for i, dt in enumerate(dates):
                close = 100.0 + idx * 10 + i * (0.15 + idx * 0.02)
                db.add(MarketData(ticker=ticker, date=dt.date(), close=close, source="seed"))
        db.commit()
    return pid


def test_risk_endpoint_returns_config_and_explainability(client: TestClient):
    pid = _seed_portfolio_and_prices(client)
    r = client.get(
        f"/api/portfolios/{pid}/risk",
        params={
            "lookback_days": 126,
            "return_frequency": "weekly",
            "confidence_level": 0.99,
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["config_used"]["lookback_days"] == 126
    assert payload["config_used"]["return_frequency"] == "weekly"
    assert payload["config_used"]["confidence_level"] == 0.99
    assert "risk_explainability" in payload
    assert "top_contributors" in payload["risk_explainability"]


def test_analytics_endpoint_returns_config_and_data_range(client: TestClient):
    pid = _seed_portfolio_and_prices(client)
    r = client.get(
        f"/api/portfolios/{pid}/analytics",
        params={
            "lookback_days": 63,
            "return_frequency": "daily",
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["config_used"]["lookback_days"] == 63
    assert payload["data_range"]["observations"] <= 63
    assert "warnings" in payload


def test_risk_includes_fx_conversion_for_non_usd_position(client: TestClient):
    pid = client.post("/api/portfolios", json={"name": "FX Case"}).json()["id"]
    client.post(
        f"/api/portfolios/{pid}/positions",
        json={
            "ticker": "7203 JT Equity",
            "quantity": 100,
            "cost_price": 2000.0,
            "currency": "JPY",
            "asset_class": "Equity",
        },
    )

    dates = pd.date_range("2024-01-01", periods=140, freq="B")
    with TestSession() as db:
        for i, dt in enumerate(dates):
            db.add(MarketData(ticker="7203 JT Equity", date=dt.date(), close=2000.0 + i * 5.0, source="seed"))
        db.commit()

    without_fx = client.get(f"/api/portfolios/{pid}/risk")
    assert without_fx.status_code == 200
    payload_no_fx = without_fx.json()
    assert any("FX series for JPY->USD not found" in w for w in payload_no_fx.get("warnings", []))

    with TestSession() as db:
        for i, dt in enumerate(dates):
            # Rising JPYUSD adds extra base-currency return.
            db.add(MarketData(ticker="JPYUSD Curncy", date=dt.date(), close=0.0070 + i * 0.000001, source="seed"))
        db.commit()

    with_fx = client.get(f"/api/portfolios/{pid}/risk")
    assert with_fx.status_code == 200
    payload_fx = with_fx.json()
    assert payload_fx.get("fx_used", {}).get("JPY") == "JPYUSD Curncy"
    assert payload_fx["volatility"] != payload_no_fx["volatility"]


def test_base_currency_parameter_is_reflected(client: TestClient):
    pid = _seed_portfolio_and_prices(client)
    r = client.get(
        f"/api/portfolios/{pid}/analytics",
        params={"base_currency": "JPY", "lookback_days": 63},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["base_currency"] == "JPY"
