import numpy as np
import pandas as pd

from backtest.engine import BacktestEngine


def _deterministic_returns(periods: int = 25) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")
    data = np.full((periods, 3), 0.001)
    return pd.DataFrame(data, index=dates, columns=["AssetA", "AssetB", "AssetC"])


def test_backtest_run_monthly(sample_returns):
    engine = BacktestEngine(rebalance_freq="ME")

    # Simple allocator: static equal weight
    def equal_weight_allocator(history):
        # Ignores history, returns 1/N
        n = history.shape[1]
        return pd.Series(1 / n, index=history.columns)

    lookback = 10

    # Run backtest
    result = engine.run(sample_returns, equal_weight_allocator, lookback=lookback)
    weight_sums = result.weights.sum(axis=1)

    assert result.returns.index.equals(sample_returns.index)
    assert len(result.weights) > 0

    # The strategy should stay in cash until enough history exists, then invest immediately.
    assert np.allclose(weight_sums.iloc[:lookback].values, 0.0)
    assert np.allclose(weight_sums.iloc[lookback:].values, 1.0)
    assert np.allclose(result.weights.iloc[lookback].values, np.repeat(1 / 3, 3))

    metrics = result.returns
    assert not metrics.isna().any()


def test_backtest_rebalance_alignment(sample_returns):
    # Test that rebalancing actually happens at month ends
    engine = BacktestEngine(rebalance_freq="ME")

    call_count = 0

    def spy_allocator(history):
        nonlocal call_count
        call_count += 1
        return pd.Series(1 / 3, index=history.columns)

    engine.run(sample_returns, spy_allocator, lookback=10)

    # Sample has 100 business days, approx 5 months.
    # Should rebalance roughly 4-5 times.
    assert call_count >= 3


def test_backtest_skips_scheduled_rebalance_when_drift_below_threshold():
    returns = _deterministic_returns()
    engine = BacktestEngine(rebalance_freq="ME")
    targets = iter([
        pd.Series([0.60, 0.40, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
    ])

    def allocator(_history):
        return next(targets)

    result = engine.run(
        returns,
        allocator,
        lookback=5,
        rebalance_threshold=0.05,
    )

    assert np.allclose(result.weights.loc["2024-01-31"].values, [0.60, 0.40, 0.00])


def test_backtest_rebalances_when_drift_breaches_threshold():
    returns = _deterministic_returns()
    engine = BacktestEngine(rebalance_freq="ME")
    targets = iter([
        pd.Series([0.60, 0.40, 0.00], index=returns.columns),
        pd.Series([0.75, 0.25, 0.00], index=returns.columns),
        pd.Series([0.75, 0.25, 0.00], index=returns.columns),
    ])

    def allocator(_history):
        return next(targets)

    result = engine.run(
        returns,
        allocator,
        lookback=5,
        rebalance_threshold=0.05,
    )

    assert np.allclose(result.weights.loc["2024-01-31"].values, [0.75, 0.25, 0.00])


def test_backtest_default_rebalance_behavior_is_unchanged_without_threshold():
    returns = _deterministic_returns()
    engine = BacktestEngine(rebalance_freq="ME")
    targets = iter([
        pd.Series([0.60, 0.40, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
    ])

    def allocator(_history):
        return next(targets)

    result = engine.run(returns, allocator, lookback=5)

    assert np.allclose(result.weights.loc["2024-01-31"].values, [0.62, 0.38, 0.00])


def test_backtest_tracks_turnover_and_transaction_costs_for_skipped_rebalance():
    returns = _deterministic_returns()
    engine = BacktestEngine(rebalance_freq="ME")
    targets = iter([
        pd.Series([0.60, 0.40, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
        pd.Series([0.62, 0.38, 0.00], index=returns.columns),
    ])

    def allocator(_history):
        return next(targets)

    result = engine.run(
        returns,
        allocator,
        lookback=5,
        cost_bps=10.0,
        rebalance_threshold=0.05,
    )

    first_trade_date = returns.index[5]
    assert np.isclose(result.turnover.loc[first_trade_date], 1.0)
    assert np.isclose(result.transaction_costs.loc[first_trade_date], 0.001)
    assert np.isclose(result.turnover.loc["2024-01-31"], 0.0)
    assert np.isclose(result.transaction_costs.loc["2024-01-31"], 0.0)


def test_backtest_tracks_turnover_and_transaction_costs_for_executed_rebalance():
    returns = _deterministic_returns()
    engine = BacktestEngine(rebalance_freq="ME")
    targets = iter([
        pd.Series([0.60, 0.40, 0.00], index=returns.columns),
        pd.Series([0.75, 0.25, 0.00], index=returns.columns),
        pd.Series([0.75, 0.25, 0.00], index=returns.columns),
    ])

    def allocator(_history):
        return next(targets)

    result = engine.run(
        returns,
        allocator,
        lookback=5,
        cost_bps=10.0,
        rebalance_threshold=0.05,
    )

    assert np.isclose(result.turnover.loc["2024-01-31"], 0.30)
    assert np.isclose(result.transaction_costs.loc["2024-01-31"], 0.0003)
