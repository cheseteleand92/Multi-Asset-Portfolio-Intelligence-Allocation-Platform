# Drift Threshold Rebalancing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an optional drift threshold that suppresses scheduled rebalances unless the proposed target weights differ enough from current holdings to justify trading.

**Architecture:** Extend `BacktestEngine.run` with a threshold-aware rebalance decision while preserving eager first allocation and current default behavior. Propagate the new parameter through the backtest service so both strategy and benchmark runs use the same trading rule, then lock the behavior with focused engine and API tests.

**Tech Stack:** Python 3.10, pandas, pytest, FastAPI

---

### Task 1: Define engine behavior with failing tests

**Files:**
- Modify: `tests/backtest/test_engine.py`
- Modify: `backtest/engine.py`

**Step 1: Write the failing test**

Add tests that:

- skip a scheduled rebalance when the new target is within the configured drift threshold
- execute a scheduled rebalance when the new target breaches the threshold
- preserve current calendar rebalancing when the threshold is omitted

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: FAIL because `BacktestEngine.run` does not accept or enforce `rebalance_threshold`.

**Step 3: Write minimal implementation**

Update `BacktestEngine.run` to accept `rebalance_threshold`, compute target-vs-current drift on scheduled dates, and only charge turnover/cost when a trade actually happens.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/backtest/test_engine.py backtest/engine.py
git commit -m "feat(backtest): add drift threshold rebalancing"
```

### Task 2: Expose the threshold through the service and API

**Files:**
- Modify: `backend/domain/backtest/service.py`
- Modify: `tests/api/test_backtest.py`

**Step 1: Write the failing test**

Add an API test that posts `rebalance_threshold`, retrieves the backtest detail payload, and verifies the parameter is preserved and the run still returns NAV/benchmark series.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because the new parameter is ignored or not reflected in the saved params.

**Step 3: Write minimal implementation**

Parse `rebalance_threshold` in the service and pass it into both strategy and benchmark engine runs.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/domain/backtest/service.py tests/api/test_backtest.py
git commit -m "feat(api): wire drift threshold through backtests"
```

### Task 3: Verify the research workflow stays clean

**Files:**
- Modify: `README.md` if usage docs need the new parameter

**Step 1: Run focused verification**

Run:

- `python -m pytest tests/backtest/test_engine.py -q`
- `python -m pytest tests/api/test_backtest.py -q`

Expected: PASS

**Step 2: Run repo verification**

Run:

- `python -m pytest -q`
- `ruff check backend tests`

Expected: PASS

**Step 3: Update docs only if needed**

Document the new optional parameter if it materially improves reproducibility for research users.

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document drift threshold rebalancing"
```
