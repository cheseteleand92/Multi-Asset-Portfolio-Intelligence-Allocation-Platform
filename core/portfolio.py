"""Portfolio container and analytics orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class Portfolio:
    """Represents a multi-asset portfolio state.

    Attributes:
        weights: Current portfolio weights indexed by ticker.
        benchmark_weights: Benchmark weights indexed by ticker.
        base_currency: Reporting currency.
    """

    weights: pd.Series
    benchmark_weights: pd.Series
    base_currency: str = "USD"
    metadata: Dict[str, str] = field(default_factory=dict)

    def normalize_weights(self) -> pd.Series:
        """Return normalized weights summing to 1."""
        if np.isclose(self.weights.abs().sum(), 0.0):
            raise ValueError("Weight vector is all zeros.")
        self.weights = self.weights / self.weights.sum()
        return self.weights

    def active_weights(self) -> pd.Series:
        """Compute active weights versus benchmark."""
        aligned = pd.concat([self.weights, self.benchmark_weights], axis=1).fillna(0.0)
        aligned.columns = ["portfolio", "benchmark"]
        return aligned["portfolio"] - aligned["benchmark"]

    def nav_series(self, returns: pd.DataFrame, nav0: float = 100.0) -> pd.Series:
        """Compute historical NAV from asset returns and current weights."""
        common = returns.columns.intersection(self.weights.index)
        pnl = returns[common].mul(self.weights[common], axis=1).sum(axis=1)
        return nav0 * (1.0 + pnl).cumprod()
