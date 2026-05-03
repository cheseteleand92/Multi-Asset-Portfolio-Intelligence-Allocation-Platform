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
    turnover: pd.Series
    transaction_costs: pd.Series


class BacktestEngine:
    """Generic monthly rebalancing walk-forward backtester."""

    def __init__(self, rebalance_freq: str = "ME") -> None:
        self.rebalance_freq = rebalance_freq

    def run(
        self,
        asset_returns: pd.DataFrame,
        allocator: Callable[[pd.DataFrame], pd.Series],
        lookback: int = 252,
        cost_bps: float = 0.0,
        rebalance_threshold: float | None = None,
    ) -> BacktestResult:
        """Run walk-forward test with rebalanced weights.
        
        Args:
            cost_bps: Linear transaction cost in basis points (e.g. 10.0 for 10bps).
        """
        dates = asset_returns.index
        rebalance_freq = "ME" if self.rebalance_freq == "M" else self.rebalance_freq
        try:
            rebalance_dates = dates.to_series().resample(rebalance_freq).last().dropna()
        except ValueError:
            # Compatibility fallback between pandas versions:
            # some accept "ME" while older versions expect "M".
            alt_freq = "M" if rebalance_freq == "ME" else "ME"
            rebalance_dates = dates.to_series().resample(alt_freq).last().dropna()
        # Ensure rebalance dates align with available data
        rebalance_dates = rebalance_dates.map(lambda d: dates[dates <= d].max()).unique()
        rebalance_dates = pd.DatetimeIndex(rebalance_dates).dropna()
        
        current_weights = pd.Series(0.0, index=asset_returns.columns)
        drift_threshold = (
            None if rebalance_threshold is None else max(0.0, float(rebalance_threshold))
        )
        rets = []
        turnover_hist = []
        cost_hist = []
        w_hist = []

        for i, dt in enumerate(dates):
            cost_drag = 0.0
            turnover = 0.0

            is_first_eligible_day = i == lookback
            is_scheduled_rebalance = i >= lookback and dt in rebalance_dates.values
            if i >= lookback and (is_first_eligible_day or is_scheduled_rebalance):
                window = asset_returns.iloc[i - lookback : i]
                target_weights = allocator(window).reindex(asset_returns.columns).fillna(0.0)

                should_trade = True
                if (
                    not is_first_eligible_day
                    and drift_threshold is not None
                    and drift_threshold > 0.0
                ):
                    drift = float((target_weights - current_weights).abs().sum())
                    should_trade = drift >= drift_threshold

                if should_trade:
                    turnover = float((target_weights - current_weights).abs().sum())
                    cost_drag = turnover * cost_bps * 1e-4
                    current_weights = target_weights

            day_ret = float((asset_returns.loc[dt] * current_weights).sum())
            rets.append(day_ret - cost_drag)
            turnover_hist.append(turnover)
            cost_hist.append(cost_drag)
            w_hist.append(current_weights.rename(dt))

        returns = pd.Series(rets, index=dates)
        nav = (1 + returns).cumprod() * 100
        weights = pd.DataFrame(w_hist)
        turnover_series = pd.Series(turnover_hist, index=dates)
        transaction_costs = pd.Series(cost_hist, index=dates)
        return BacktestResult(
            returns=returns,
            nav=nav,
            weights=weights,
            turnover=turnover_series,
            transaction_costs=transaction_costs,
        )
