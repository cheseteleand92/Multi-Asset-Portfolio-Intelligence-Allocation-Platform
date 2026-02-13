
import pytest
import pandas as pd
import numpy as np
from core.portfolio import Portfolio

def test_portfolio_normalization():
    w = pd.Series([0.5, 1.5], index=["A", "B"])
    p = Portfolio(weights=w, benchmark_weights=w)
    p.normalize_weights()
    assert np.isclose(p.weights.sum(), 1.0)
    assert np.isclose(p.weights["A"], 0.25)

def test_portfolio_normalization_zero_sum():
    # Case: Weights sum to 0 but abs sum > 0
    w = pd.Series([0.5, -0.5], index=["A", "B"])
    p = Portfolio(weights=w, benchmark_weights=w)
    
    # Should raise ValueError as per our fix
    with pytest.raises(ValueError, match="Net weight is zero"):
        p.normalize_weights()

def test_portfolio_normalization_all_zeros():
    w = pd.Series([0.0, 0.0], index=["A", "B"])
    p = Portfolio(weights=w, benchmark_weights=w)
    # Should return as is (all zeros)
    p.normalize_weights()
    assert (p.weights == 0).all()
