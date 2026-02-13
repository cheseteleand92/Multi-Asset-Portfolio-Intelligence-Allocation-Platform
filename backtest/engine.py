"""Walk-forward backtest engine for allocation strategies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class BacktestResult:
    """Backtest outputs."""

    returns: pd.Series
    nav: pd.Series
    weights: pd.DataFrame


class BacktestEngine:
    """Generic monthly rebalancing walk-forward backtester."""

    def __init__(self, rebalance_freq: str = "M") -> None:
        self.rebalance_freq = rebalance_freq

    def run(
        self,
        asset_returns: pd.DataFrame,
        allocator: Callable[[pd.DataFrame], pd.Series],
        lookback: int = 252,
        cost_bps: float = 0.0,
    ) -> BacktestResult:
        """Run walk-forward test with rebalanced weights.
        
        Args:
            cost_bps: Linear transaction cost in basis points (e.g. 10.0 for 10bps).
        """
        dates = asset_returns.index
        rebalance_dates = dates.to_series().resample(self.rebalance_freq).last().dropna()
        # Ensure rebalance dates align with available data
        rebalance_dates = rebalance_dates.map(lambda d: dates[dates <= d].max()).unique()
        rebalance_dates = pd.DatetimeIndex(rebalance_dates).dropna()
        
        current_weights = pd.Series(0.0, index=asset_returns.columns)
        rets = []
        w_hist = []

        for i, dt in enumerate(dates):
            cost_drag = 0.0
            
            if dt in rebalance_dates.values and i >= lookback:
                window = asset_returns.iloc[i - lookback : i]
                new_weights = allocator(window).reindex(asset_returns.columns).fillna(0.0)
                
                # Calculate turnover and cost
                turnover = (new_weights - current_weights).abs().sum()
                cost_drag = turnover * cost_bps * 1e-4
                
                current_weights = new_weights
            
            day_ret = float((asset_returns.loc[dt] * current_weights).sum())
            rets.append(day_ret - cost_drag)
            w_hist.append(current_weights.rename(dt))

        returns = pd.Series(rets, index=dates)
        nav = (1 + returns).cumprod() * 100
        weights = pd.DataFrame(w_hist)
        return BacktestResult(returns=returns, nav=nav, weights=weights)
