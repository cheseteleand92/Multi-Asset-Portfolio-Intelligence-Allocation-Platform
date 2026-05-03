"""Risk budgeting optimization engine (ERC/TRC/capped budgets)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import cvxpy as cp
import numpy as np
import pandas as pd


@dataclass
class RiskBudgetingConfig:
    """Constraint set for risk budgeting.

    Attributes:
        long_only: Enforce non-negative weights.
        max_weight: Asset-level hard cap.
        turnover_penalty: L1 turnover penalty coefficient.
        transaction_cost_penalty: Linear transaction-cost penalty coefficient.
        vol_target: Optional volatility ceiling.
        tracking_error_limit: Optional tracking-error ceiling versus benchmark.
    """

    long_only: bool = True
    max_weight: float = 0.30
    turnover_penalty: float = 0.0
    transaction_cost_penalty: float = 0.0
    vol_target: Optional[float] = None
    tracking_error_limit: Optional[float] = None


@dataclass
class RiskBudgetingResult:
    """Optimization output bundle."""

    weights: pd.Series
    marginal_risk_contribution: pd.Series
    risk_contribution: pd.Series


class RiskBudgetingEngine:
    """Solve ERC/TRC under realistic portfolio constraints with cvxpy.

    Variance decomposition used for risk contributions:
        RC_i = w_i (\\Sigma w)_i
        MRC_i = (\\Sigma w)_i / sigma_p
    """

    def __init__(self, config: Optional[RiskBudgetingConfig] = None) -> None:
        self.config = config or RiskBudgetingConfig()

    def _constraints(self, w: cp.Variable) -> list:
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
        benchmark_weights: Optional[pd.Series] = None,
        factor_exposures: Optional[pd.DataFrame] = None,
        factor_risk_caps: Optional[Dict[str, float]] = None,
        region_map: Optional[Dict[str, str]] = None,
        regional_risk_caps: Optional[Dict[str, float]] = None,
    ) -> RiskBudgetingResult:
        """Target Risk Contribution solver.

        Minimizes squared error between realized and target contribution budgets,
        while allowing additional risk and implementation constraints.
        """
        names = list(cov.index)
        sigma = cov.loc[names, names].values
        n = len(names)
        w = cp.Variable(n)

        rc_raw = cp.multiply(w, sigma @ w)
        total_var = cp.quad_form(w, sigma)
        target = target_risk_budget.loc[names].values
        objective_terms = [cp.sum_squares(rc_raw - target * total_var)]

        base = np.zeros(n)
        if current_weights is not None:
            base = current_weights.reindex(names).fillna(0.0).values
            if self.config.turnover_penalty > 0:
                objective_terms.append(self.config.turnover_penalty * cp.norm1(w - base))

        if transaction_costs is not None and self.config.transaction_cost_penalty > 0:
            tc = transaction_costs.reindex(names).fillna(0.0).values
            objective_terms.append(
                self.config.transaction_cost_penalty * cp.sum(cp.multiply(tc, cp.abs(w - base)))
            )

        constraints = self._constraints(w)

        if self.config.vol_target is not None:
            constraints.append(cp.quad_form(w, sigma) <= self.config.vol_target**2)

        if self.config.tracking_error_limit is not None and benchmark_weights is not None:
            bw = benchmark_weights.reindex(names).fillna(0.0).values
            diff = w - bw
            constraints.append(cp.quad_form(diff, sigma) <= self.config.tracking_error_limit**2)

        if factor_exposures is not None and factor_risk_caps is not None:
            b = factor_exposures.reindex(index=names).fillna(0.0)
            for factor, cap in factor_risk_caps.items():
                if factor in b.columns:
                    constraints.append(cp.abs(b[factor].values @ w) <= cap)

        if region_map is not None and regional_risk_caps is not None:
            for region, cap in regional_risk_caps.items():
                idx = [i for i, a in enumerate(names) if region_map.get(a) == region]
                if idx:
                    constraints.append(cp.sum(w[idx]) <= cap)

        problem = cp.Problem(cp.Minimize(cp.sum(objective_terms)), constraints)
        problem.solve(solver=cp.SCS, verbose=False)
        if w.value is None:
            raise RuntimeError(f"Risk budgeting optimization failed: {problem.status}")

        sol = pd.Series(np.array(w.value).flatten(), index=names)
        rc, mrc = self.risk_contribution_table(sol, cov)
        return RiskBudgetingResult(
            weights=sol,
            marginal_risk_contribution=mrc,
            risk_contribution=rc,
        )

    def solve_erc(self, cov: pd.DataFrame, **kwargs) -> RiskBudgetingResult:
        """Equal Risk Contribution allocation solved as TRC with equal budgets."""
        target = pd.Series(1 / len(cov), index=cov.index)
        return self.solve_trc(cov=cov, target_risk_budget=target, **kwargs)

    @staticmethod
    def risk_contribution_table(
        weights: pd.Series, cov: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
        """Return total and marginal risk contribution tables."""
        sigma = cov.loc[weights.index, weights.index].values
        w = weights.values
        port_vol = float(np.sqrt(w.T @ sigma @ w))
        mrc = pd.Series((sigma @ w) / (port_vol if port_vol else 1.0), index=weights.index)
        rc = weights * mrc
        return rc, mrc
