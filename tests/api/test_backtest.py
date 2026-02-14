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


def _seed_prices():
    tickers = ["AAPL US Equity", "MSFT US Equity", "GOOG US Equity"]
    dates = pd.date_range("2024-01-01", periods=140, freq="B")
    with TestSession() as db:
        for idx, ticker in enumerate(tickers):
            for i, dt in enumerate(dates):
                close = 100.0 + idx * 7.0 + i * (0.12 + 0.01 * idx)
                db.add(MarketData(ticker=ticker, date=dt.date(), close=close, source="seed"))
        db.commit()


def _create_portfolio_with_positions(client: TestClient) -> int:
    portfolio_id = client.post("/api/portfolios", json={"name": "BT"}).json()["id"]
    for ticker in ["AAPL US Equity", "MSFT US Equity", "GOOG US Equity"]:
        r = client.post(
            f"/api/portfolios/{portfolio_id}/positions",
            json={
                "ticker": ticker,
                "quantity": 100,
                "cost_price": 100.0,
                "currency": "USD",
                "asset_class": "Equity",
            },
        )
        assert r.status_code == 201
    _seed_prices()
    return portfolio_id


def test_list_backtest_strategies(client: TestClient):
    r = client.get("/api/backtests/strategies")
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()}
    assert {"hrp", "equal_weight", "mean_variance", "erc"}.issubset(ids)


def test_list_backtest_benchmarks(client: TestClient):
    r = client.get("/api/backtests/benchmarks")
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()}
    assert {"none", "hrp", "equal_weight", "mean_variance", "erc"}.issubset(ids)


@pytest.mark.parametrize("strategy", ["hrp", "equal_weight", "mean_variance", "erc"])
def test_run_backtest_for_each_strategy(client: TestClient, strategy: str):
    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": strategy,
            "benchmark": "equal_weight",
            "cost_bps": 5,
            "lookback_days": 21,
        },
    )
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["strategy"] == strategy
    assert len(payload["nav"]) > 0
    assert len(payload["benchmark"]) > 0


def test_run_backtest_without_benchmark(client: TestClient):
    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "hrp",
            "benchmark": "none",
            "cost_bps": 5,
            "lookback_days": 21,
        },
    )
    assert create.status_code == 201
    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["benchmark"] == []


def test_backtest_precheck_reports_missing_data(client: TestClient):
    portfolio_id = client.post("/api/portfolios", json={"name": "BT Precheck"}).json()["id"]
    client.post(
        f"/api/portfolios/{portfolio_id}/positions",
        json={
            "ticker": "AAPL US Equity",
            "quantity": 100,
            "cost_price": 100.0,
            "currency": "USD",
            "asset_class": "Equity",
        },
    )
    client.post(
        f"/api/portfolios/{portfolio_id}/positions",
        json={
            "ticker": "MISSING US Equity",
            "quantity": 100,
            "cost_price": 100.0,
            "currency": "USD",
            "asset_class": "Equity",
        },
    )
    _seed_prices()
    res = client.get(f"/api/portfolios/{portfolio_id}/backtests/precheck")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is False
    assert "MISSING US Equity" in payload["tickers_missing_data"]
