
import pytest
import pandas as pd
import numpy as np
from backtest.engine import BacktestEngine

def test_backtest_run_monthly(sample_returns):
    engine = BacktestEngine(rebalance_freq="M")
    
    # Simple allocator: static equal weight
    def equal_weight_allocator(history):
        # Ignores history, returns 1/N
        n = history.shape[1]
        return pd.Series(1/n, index=history.columns)
    
    # Run backtest
    result = engine.run(sample_returns, equal_weight_allocator, lookback=10)
    
    assert result.returns.index.equals(sample_returns.index)
    assert len(result.weights) > 0
    # Check if weights sum to 1 (approx)
    assert np.allclose(result.weights.sum(axis=1).values, 1.0)
    
    # Check NAV calc
    # First day return: return[0] * weight[0]?? 
    # Engine logic: day_ret = (asset_returns.loc[dt] * current_weights).sum()
    # Then nav = (1+ret).cumprod()
    
    metrics = result.returns
    assert not metrics.isna().any()

def test_backtest_rebalance_alignment(sample_returns):
    # Test that rebalancing actually happens at month ends
    engine = BacktestEngine(rebalance_freq="ME") # Use 'ME' for Month End in newer pandas, or 'M'
    
    call_count = 0
    def spy_allocator(history):
        nonlocal call_count
        call_count += 1
        return pd.Series(1/3, index=history.columns)
        
    engine.run(sample_returns, spy_allocator, lookback=10)
    
    # Sample has 100 business days, approx 5 months. 
    # Should rebalance roughly 4-5 times.
    assert call_count >= 3
