import pytest
import numpy as np
import pandas as pd
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
