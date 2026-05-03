import warnings

import numpy as np
import pandas as pd

from core.optimization import estimate_covariance, hierarchical_risk_parity


def test_hierarchical_risk_parity_handles_near_perfect_correlation():
    dates = pd.date_range("2024-01-01", periods=26, freq="B")
    prices = pd.DataFrame(
        {
            "AAPL": [100.0 + i * 0.12 for i in range(len(dates))],
            "MSFT": [107.0 + i * 0.13 for i in range(len(dates))],
            "GOOG": [114.0 + i * 0.14 for i in range(len(dates))],
        },
        index=dates,
    )
    cov = prices.pct_change().dropna().tail(21).cov()

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        weights = hierarchical_risk_parity(cov)

    assert np.isfinite(weights.to_numpy()).all()
    assert np.isclose(weights.sum(), 1.0)


def test_estimate_covariance_sample_matches_pandas(sample_returns):
    estimated = estimate_covariance(sample_returns, method="sample")

    pd.testing.assert_frame_equal(estimated, sample_returns.cov())


def test_estimate_covariance_methods_are_symmetric_and_finite(sample_returns):
    for method in ["ewma", "shrinkage", "ensemble"]:
        estimated = estimate_covariance(sample_returns, method=method)

        assert estimated.index.equals(sample_returns.columns)
        assert estimated.columns.equals(sample_returns.columns)
        assert np.allclose(estimated.values, estimated.values.T)
        assert np.isfinite(estimated.to_numpy()).all()


def test_estimate_covariance_ensemble_differs_from_sample(sample_returns):
    sample_cov = estimate_covariance(sample_returns, method="sample")
    ensemble_cov = estimate_covariance(sample_returns, method="ensemble")

    assert not np.allclose(sample_cov.values, ensemble_cov.values)
