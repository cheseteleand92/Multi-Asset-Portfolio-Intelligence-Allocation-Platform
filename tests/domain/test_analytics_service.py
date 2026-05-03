import numpy as np
import pandas as pd
import pytest

from backend.domain.analytics import service


@pytest.fixture()
def returns():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    tickers = ["A", "B", "C", "D"]
    data = np.random.randn(252, 4) * 0.01
    return pd.DataFrame(data, index=dates, columns=tickers)


@pytest.fixture()
def weights():
    return {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}


def test_compute_risk_returns_var(returns, weights):
    result = service.compute_risk(returns, weights)
    assert "var_95" in result
    assert 0 < result["var_95"] < 0.1


def test_compute_risk_returns_trc(returns, weights):
    result = service.compute_risk(returns, weights)
    assert "trc" in result
    assert set(result["trc"].keys()) == {"A", "B", "C", "D"}


def test_what_if_changes_var(returns, weights):
    base = service.compute_risk(returns, weights)
    adjusted = {"A": 0.1, "B": 0.1, "C": 0.4, "D": 0.4}
    result = service.compute_risk(returns, adjusted)
    assert result["var_95"] != base["var_95"]


def test_compute_risk_returns_config_and_explainability(returns, weights):
    result = service.compute_risk(
        returns,
        weights,
        config={
            "lookback_days": 126,
            "return_frequency": "weekly",
            "confidence_level": 0.99,
        },
    )
    assert "config_used" in result
    assert result["config_used"]["lookback_days"] == 126
    assert result["config_used"]["return_frequency"] == "weekly"
    assert result["config_used"]["confidence_level"] == 0.99
    assert "data_range" in result
    assert "warnings" in result
    assert "risk_explainability" in result
    assert "weight_effect" in result["risk_explainability"]


def test_compute_nav_respects_parameters(returns, weights):
    result = service.compute_nav(
        returns,
        weights,
        config={
            "lookback_days": 63,
            "return_frequency": "daily",
            "risk_free_rate": 0.02,
        },
    )
    assert "config_used" in result
    assert result["config_used"]["lookback_days"] == 63
    assert "data_range" in result
    assert result["data_range"]["observations"] <= 63
    assert "asset_nav" in result
    assert set(result["asset_nav"].keys()) == {"A", "B", "C", "D"}
