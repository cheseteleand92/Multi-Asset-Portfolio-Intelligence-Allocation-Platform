
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_returns():
    """Generate synthetic returns for 3 assets over 100 days."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    data = np.random.normal(0, 0.01, (100, 3))
    return pd.DataFrame(data, index=dates, columns=["AssetA", "AssetB", "AssetC"])

@pytest.fixture
def sample_covariance(sample_returns):
    """Generate sample covariance matrix."""
    return sample_returns.cov()

@pytest.fixture
def sample_weights():
    """Generate equal weights for 3 assets."""
    return pd.Series([1/3, 1/3, 1/3], index=["AssetA", "AssetB", "AssetC"])
