# Regime-Aware Exposure Overlay Design

**Date:** 2026-03-07

**Scope:** Add an optional regime-aware exposure overlay for strategy backtests that scales gross exposure based on a simple market regime signal while leaving benchmarks unchanged by default.

## Problem

The current backtest stack can compare allocators, covariance methods, and trading thresholds, but it still assumes the strategy is always fully deployed once weights are set. That misses a common institutional research question: should the strategy carry the same total exposure in risk-on and risk-off conditions?

## Options

### 1. Recommended: cash overlay

- Wrap the existing allocator in a regime-aware exposure scaler.
- In `risk_on`, keep exposure at `risk_on_exposure`.
- In `risk_off`, scale portfolio weights down to `risk_off_exposure` and leave the residual in cash.
- Benchmarks do not use the overlay unless explicitly requested.

Trade-off: simple and robust, but it models only exposure timing, not sector/asset rotation.

### 2. Defensive rotation

- Shift risk-off weight into a defensive sleeve rather than cash.

Trade-off: more realistic for multi-asset rotation, but it requires a stable asset classification layer that this repo does not yet enforce.

### 3. Regime-conditioned optimizer

- Swap risk aversion, covariance method, or constraints based on regime.

Trade-off: highest sophistication, but it expands scope materially and makes debugging much harder.

## Decision

Implement option 1.

## Architecture

- Reuse the existing regime heuristic already available in `backend/domain/signals/service.py`.
- Extend allocator construction so the base allocator can be wrapped by an exposure overlay.
- Support optional params:
  - `regime_overlay`
  - `risk_on_exposure`
  - `risk_off_exposure`
- Apply the overlay to the strategy allocator by default, but keep benchmark allocators unmodified unless `benchmark_regime_overlay` is explicitly enabled.

## Validation

- Add an API test that forces `risk_off` and proves the strategy allocator is scaled down while the benchmark remains fully invested.
- Confirm default behavior stays unchanged when the overlay is omitted.
- Run targeted tests, then `python -m pytest -q`, then `ruff check backend tests backtest core examples`.
