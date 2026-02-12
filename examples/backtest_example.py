"""Step 7: Example walk-forward backtest script."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import BacktestEngine
from core.optimization import mean_variance_opt


def allocator(window_returns: pd.DataFrame) -> pd.Series:
    mu = window_returns.mean() * 252
    cov = window_returns.cov() * 252
    return mean_variance_opt(mu, cov, risk_aversion=6.0, max_weight=0.4)


def main() -> None:
    np.random.seed(7)
    dates = pd.bdate_range("2020-01-01", periods=900)
    assets = ["US_EQ", "JP_EQ", "CN_A", "GLB_BOND", "CREDIT", "FX", "CMDTY"]
    raw = np.random.normal(0.0003, 0.01, (len(dates), len(assets)))
    returns = pd.DataFrame(raw, index=dates, columns=assets)

    engine = BacktestEngine(rebalance_freq="M")
    result = engine.run(returns, allocator=allocator, lookback=252)

    print("Final NAV:", round(result.nav.iloc[-1], 2))
    print("Annualized Return:", round(result.returns.mean() * 252, 4))
    print("Annualized Vol:", round(result.returns.std() * (252**0.5), 4))


if __name__ == "__main__":
    main()
