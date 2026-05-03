# Backtest Stability Design

**Date:** 2026-03-07

**Scope:** Stabilize the backtest engine behavior and make the documented test workflow match the working environment.

## Problem

The walk-forward engine remains fully in cash until the first scheduled month-end rebalance after `lookback` observations exist. That makes the strategy appear uninvested for longer than necessary and causes the current regression test to fail. Separately, the repo documentation still suggests generic `pytest` usage even though `python -m pytest` is the reliable invocation in this environment.

## Decision

Use an eager first allocation:

- Before `lookback` observations are available, weights remain zero.
- On the first eligible day (`i == lookback`), compute and apply weights immediately.
- After initialization, keep using the configured rebalance schedule for future changes.
- Transaction cost drag is applied only when weights change.

## Rationale

- Matches the user-approved behavior: invest as soon as enough history exists.
- Preserves the rebalance schedule without inventing synthetic pre-start dates.
- Keeps turnover and cost handling easy to reason about.
- Produces a clearer, more realistic backtest state for downstream analytics.

## Validation

- Update backtest tests to assert zero exposure before the first eligible day and full investment from that day onward.
- Confirm scheduled rebalancing still occurs after initialization.
- Run the full Python test suite with `python -m pytest -q`.
- Update repo docs to recommend `python -m pytest`.
