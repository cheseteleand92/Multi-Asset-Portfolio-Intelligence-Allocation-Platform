
"""
Integration demo script to verify the full portfolio pipeline.
"""
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from core.factor_model import FactorModel
from core.optimization import mean_variance_opt, hierarchical_risk_parity
from core.risk_engine import portfolio_volatility, max_drawdown, sharpe_ratio
from backtest.engine import BacktestEngine
from backtest.cost_model import linear_cost

def generate_synthetic_data(n_assets=5, n_days=500):
    np.random.seed(42)
    dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n_days)
    names = [f"Asset_{i}" for i in range(n_assets)]
    # Correlation structure
    cov = np.random.randn(n_assets, n_assets)
    cov = cov @ cov.T
    cov[np.diag_indices_from(cov)] = 1.0
    
    # Returns
    mean_ret = np.random.uniform(0.0001, 0.0005, n_assets)
    returns = np.random.multivariate_normal(mean_ret, cov * 0.0001, n_days)
    
    return pd.DataFrame(returns, index=dates, columns=names)

def run_pipeline():
    print("--- 1. Generating Data ---")
    data = generate_synthetic_data(n_assets=6, n_days=500)
    print(f"Data shape: {data.shape}")
    
    print("\n--- 2. Optimization Strategy (HRP) ---")
    # Estimate covariance from first 252 days
    train_data = data.iloc[:252]
    test_data = data.iloc[252:]
    
    cov = train_data.cov()
    hrp_weights = hierarchical_risk_parity(cov)
    print("HRP Weights:")
    print(hrp_weights)
    
    print("\n--- 3. Backtest (Walk-Forward) ---")
    
    def allocator(history):
        # Rolling covariance HRP
        # Simple allocator that ignores returns mean (risk-based)
        cov_mat = history.cov()
        try:
            w = hierarchical_risk_parity(cov_mat)
        except:
            # Fallback to equal weight if singular
            w = pd.Series(1/history.shape[1], index=history.columns)
        return w

    engine = BacktestEngine(rebalance_freq="M")
    # Run with 10bps cost
    result = engine.run(data, allocator, lookback=126, cost_bps=10.0)
    
    print("\n--- 4. Performance Metrics ---")
    total_ret = (result.nav.iloc[-1] / result.nav.iloc[0]) - 1
    mdd = max_drawdown(result.returns)
    vol = portfolio_volatility(pd.Series(1.0, index=["Portfolio"]), pd.DataFrame([[result.returns.var()]]), annualization=252) # approximated
    # Actually calculate vol of returns series directly
    realized_vol = result.returns.std() * np.sqrt(252)
    
    print(f"Total Return: {total_ret:.2%}")
    print(f"Max Drawdown: {mdd:.2%}")
    print(f"Realized Vol: {realized_vol:.2%}")
    print(f"Final NAV:    {result.nav.iloc[-1]:.2f}")
    
    print("\n--- 5. Transaction Costs Analysis ---")
    # Approximate cost impact
    # Run without cost
    res_no_cost = engine.run(data, allocator, lookback=126, cost_bps=0.0)
    nav_diff = res_no_cost.nav.iloc[-1] - result.nav.iloc[-1]
    print(f"NAV Impact from 10bps cost: {nav_diff:.2f} points")
    
    print("\n[SUCCESS] Pipeline verified.")

if __name__ == "__main__":
    run_pipeline()
