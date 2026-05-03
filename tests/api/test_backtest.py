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
    assert detail.json()["relative_attribution"] is None


def test_backtest_detail_exposes_relative_attribution_summary(client: TestClient):
    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "hrp",
            "benchmark": "equal_weight",
            "cost_bps": 5,
            "lookback_days": 21,
        },
    )
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")

    assert detail.status_code == 200
    relative = detail.json()["relative_attribution"]
    assert {"summary", "series"}.issubset(relative.keys())
    assert {
        "annualized_active_return",
        "tracking_error",
        "information_ratio",
        "max_relative_drawdown",
        "average_active_share",
    }.issubset(relative["summary"].keys())
    assert len(relative["series"]) == len(detail.json()["nav"])
    assert {
        "date",
        "portfolio_return",
        "benchmark_return",
        "active_return",
        "active_share",
    }.issubset(relative["series"][0].keys())


def test_backtest_api_applies_regime_overlay_to_strategy_only(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_weight_sums = []

    class SpyEngine:
        def __init__(self, rebalance_freq: str = "ME") -> None:
            self.rebalance_freq = rebalance_freq

        def run(
            self,
            asset_returns,
            allocator,
            lookback=252,
            cost_bps=0.0,
            rebalance_threshold=None,
        ):
            window = asset_returns.iloc[: max(int(lookback), 21)]
            weights = allocator(window).reindex(asset_returns.columns).fillna(0.0)
            captured_weight_sums.append(round(float(weights.sum()), 6))
            dates = asset_returns.index[:3]
            nav = pd.Series([100.0, 100.0, 100.0], index=dates)
            weights_frame = pd.DataFrame([weights] * len(dates), index=dates)
            zeros = pd.Series(0.0, index=dates)
            return type(
                "Result",
                (),
                {
                    "returns": zeros,
                    "nav": nav,
                    "weights": weights_frame,
                    "turnover": zeros,
                    "transaction_costs": zeros,
                },
            )()

    monkeypatch.setattr("backend.domain.backtest.service.BacktestEngine", SpyEngine)
    monkeypatch.setattr(
        "backend.domain.backtest.service.get_regime_signal",
        lambda _window_returns: {"regime": "risk_off"},
        raising=False,
    )

    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "equal_weight",
            "benchmark": "equal_weight",
            "cost_bps": 5,
            "lookback_days": 21,
            "regime_overlay": "trend",
            "risk_on_exposure": 1.0,
            "risk_off_exposure": 0.25,
        },
    )
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")

    assert detail.status_code == 200
    assert captured_weight_sums == [0.25, 1.0]


def test_backtest_api_passes_rebalance_threshold_to_strategy_and_benchmark(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_thresholds = []

    class SpyEngine:
        def __init__(self, rebalance_freq: str = "ME") -> None:
            self.rebalance_freq = rebalance_freq

        def run(
            self,
            asset_returns,
            allocator,
            lookback=252,
            cost_bps=0.0,
            rebalance_threshold=None,
        ):
            captured_thresholds.append(rebalance_threshold)
            dates = asset_returns.index[:3]
            nav = pd.Series([100.0, 100.5, 101.0], index=dates)
            equal_weight = pd.Series(
                1 / len(asset_returns.columns),
                index=asset_returns.columns,
            )
            weights = pd.DataFrame(
                [equal_weight] * len(dates),
                index=dates,
            )
            zeros = pd.Series(0.0, index=dates)
            return type(
                "Result",
                (),
                {
                    "nav": nav,
                    "weights": weights,
                    "turnover": zeros,
                    "transaction_costs": zeros,
                },
            )()

    monkeypatch.setattr("backend.domain.backtest.service.BacktestEngine", SpyEngine)

    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "equal_weight",
            "benchmark": "equal_weight",
            "cost_bps": 5,
            "lookback_days": 21,
            "rebalance_threshold": 0.05,
        },
    )
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")

    assert detail.status_code == 200
    assert captured_thresholds == [0.05, 0.05]


def test_backtest_detail_exposes_turnover_metrics(client: TestClient):
    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "equal_weight",
            "benchmark": "none",
            "cost_bps": 10,
            "lookback_days": 21,
        },
    )
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/api/backtests/{run_id}")

    assert detail.status_code == 200
    metrics = detail.json()["metrics"]
    assert len(metrics) == len(detail.json()["nav"])
    assert {"date", "turnover", "transaction_cost"}.issubset(metrics[0].keys())
    assert any(item["turnover"] > 0 for item in metrics)


def test_backtest_api_passes_covariance_method_into_strategy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_methods = []

    def spy_estimate_covariance(window_returns, method="sample", **_kwargs):
        captured_methods.append(method)
        return window_returns.cov()

    monkeypatch.setattr(
        "backend.domain.backtest.service.estimate_covariance",
        spy_estimate_covariance,
        raising=False,
    )

    portfolio_id = _create_portfolio_with_positions(client)
    create = client.post(
        "/api/backtests",
        json={
            "portfolio_id": portfolio_id,
            "strategy": "hrp",
            "benchmark": "none",
            "cost_bps": 5,
            "lookback_days": 21,
            "covariance_method": "ensemble",
        },
    )

    assert create.status_code == 201
    assert captured_methods
    assert set(captured_methods) == {"ensemble"}


def test_backtest_sweep_returns_parameter_grid_summaries(client: TestClient):
    portfolio_id = _create_portfolio_with_positions(client)
    response = client.post(
        "/api/backtests/sweep",
        json={
            "portfolio_id": portfolio_id,
            "strategies": ["hrp"],
            "lookback_days_grid": [21, 42],
            "cost_bps_grid": [5],
            "rebalance_threshold_grid": [None, 0.05],
            "covariance_method_grid": ["sample", "ensemble"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 8
    assert len(payload["runs"]) == 8
    assert {
        "strategy",
        "lookback_days",
        "cost_bps",
        "rebalance_threshold",
        "covariance_method",
        "final_nav",
        "annualized_return",
        "annualized_vol",
        "max_drawdown",
        "average_turnover",
        "total_transaction_cost",
    }.issubset(payload["runs"][0].keys())


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
