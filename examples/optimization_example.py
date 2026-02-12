"""Step 6: Sample optimization workflow for MVO + Risk Budgeting."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.optimization import mean_variance_opt
from core.risk_budgeting import RiskBudgetingConfig, RiskBudgetingEngine


def main() -> None:
    assets = ["SPY", "EWJ", "CSI300", "GLD", "UST10", "LQD", "USDJPY", "DBC"]
    np.random.seed(42)
    exp_returns = pd.Series(np.random.uniform(0.03, 0.12, len(assets)), index=assets)
    rnd = np.random.randn(len(assets), len(assets))
    cov = pd.DataFrame(rnd.T @ rnd / 252, index=assets, columns=assets)

    mvo_weights = mean_variance_opt(exp_returns, cov, risk_aversion=8.0, max_weight=0.35)
    rb_engine = RiskBudgetingEngine(RiskBudgetingConfig(max_weight=0.35, vol_target=0.12))
    erc_weights = rb_engine.solve_erc(cov)

    print("=== Mean-Variance Weights ===")
    print(mvo_weights.round(4))
    print("\n=== ERC Weights ===")
    print(erc_weights.round(4))


if __name__ == "__main__":
    main()
