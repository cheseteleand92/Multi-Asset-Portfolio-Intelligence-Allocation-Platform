"""Risk budgeting optimization engine (ERC/TRC/capped budgets)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cvxpy as cp
import numpy as np
import pandas as pd


@dataclass
class RiskBudgetingConfig:
    """Constraint set for risk budgeting."""

    long_only: bool = True
    max_weight: float = 0.30
    turnover_penalty: float = 0.0
    transaction_cost_penalty: float = 0.0
    vol_target: Optional[float] = None


class RiskBudgetingEngine:
    """Solve ERC/TRC under realistic portfolio constraints with cvxpy."""

    def __init__(self, config: Optional[RiskBudgetingConfig] = None) -> None:
        self.config = config or RiskBudgetingConfig()

    def _constraints(self, w: cp.Variable, n: int) -> list:
        cons = [cp.sum(w) == 1]
        if self.config.long_only:
            cons.append(w >= 0)
        cons.append(w <= self.config.max_weight)
        return cons

    def solve_trc(
        self,
        cov: pd.DataFrame,
        target_risk_budget: pd.Series,
        current_weights: Optional[pd.Series] = None,
        transaction_costs: Optional[pd.Series] = None,
    ) -> pd.Series:
        """Target Risk Contribution solver.

        Minimize squared distance between realized risk contributions and target budgets.
        """
        names = cov.index
        sigma = cov.values
        n = len(names)
        w = cp.Variable(n)
        rc_raw = cp.multiply(w, sigma @ w)
        total_var = cp.quad_form(w, sigma)
        target = target_risk_budget.loc[names].values
        objective_terms = [cp.sum_squares(rc_raw - target * total_var)]

        if current_weights is not None and self.config.turnover_penalty > 0:
            objective_terms.append(self.config.turnover_penalty * cp.norm1(w - current_weights.loc[names].values))

        if transaction_costs is not None and self.config.transaction_cost_penalty > 0:
            objective_terms.append(
                self.config.transaction_cost_penalty
                * cp.sum(cp.multiply(transaction_costs.loc[names].values, cp.abs(w - (current_weights.loc[names].values if current_weights is not None else 0))))
            )

        constraints = self._constraints(w, n)
        if self.config.vol_target is not None:
            constraints.append(cp.quad_form(w, sigma) <= self.config.vol_target**2)

        problem = cp.Problem(cp.Minimize(cp.sum(objective_terms)), constraints)
        problem.solve(solver=cp.SCS, verbose=False)
        if w.value is None:
            raise RuntimeError(f"Risk budgeting optimization failed: {problem.status}")

        sol = pd.Series(np.array(w.value).flatten(), index=names)
        return sol

    def solve_erc(self, cov: pd.DataFrame, **kwargs) -> pd.Series:
        """Equal Risk Contribution allocation solved as TRC with equal budgets."""
        target = pd.Series(1 / len(cov), index=cov.index)
        return self.solve_trc(cov=cov, target_risk_budget=target, **kwargs)
