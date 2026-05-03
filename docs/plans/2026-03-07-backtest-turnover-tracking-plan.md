# Backtest Turnover Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface turnover and transaction-cost series from the walk-forward engine to persisted backtest results and API consumers.

**Architecture:** Add the new series to the in-memory `BacktestResult`, persist them through `metrics_json` on each result row, and expose them as a separate `metrics` array in the backtest detail response. Keep existing `nav`, `weights_json`, and benchmark behavior unchanged.

**Tech Stack:** Python 3.10, pandas, pytest, FastAPI, SQLAlchemy

---

### Task 1: Define turnover output in the engine with failing tests

**Files:**
- Modify: `tests/backtest/test_engine.py`
- Modify: `backtest/engine.py`

**Step 1: Write the failing test**

Add assertions that:

- initial allocation records full turnover from cash into target weights
- skipped rebalance records zero turnover and zero transaction cost
- executed rebalance records the realized turnover and cost

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: FAIL because `BacktestResult` does not expose turnover metrics.

**Step 3: Write minimal implementation**

Track per-date turnover and transaction cost inside `BacktestEngine.run` and return them on `BacktestResult`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: PASS

### Task 2: Persist and expose metrics through the API

**Files:**
- Modify: `backend/domain/backtest/service.py`
- Modify: `backend/domain/backtest/router.py`
- Modify: `tests/api/test_backtest.py`

**Step 1: Write the failing test**

Add an API test that runs a backtest, fetches its detail payload, and verifies the returned `metrics` series contains `turnover` and `transaction_cost`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because metrics are not persisted or not returned.

**Step 3: Write minimal implementation**

Persist the metrics in `metrics_json` for each result row and parse them back into the detail response.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

### Task 3: Verify repo health

**Files:**
- Modify: `README.md` only if the new metrics need explicit documentation

**Step 1: Run focused checks**

Run:

- `python -m pytest tests/backtest/test_engine.py -q`
- `python -m pytest tests/api/test_backtest.py -q`

Expected: PASS

**Step 2: Run full checks**

Run:

- `python -m pytest -q`
- `ruff check backend tests backtest examples`

Expected: PASS
