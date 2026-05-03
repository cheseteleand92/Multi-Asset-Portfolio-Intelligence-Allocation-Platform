# Covariance Ensemble and Backtest Sweeps Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make covariance estimation configurable for research backtests and add a sweep endpoint that compares parameter combinations without manual repetition.

**Architecture:** Add a reusable covariance estimator in `core/optimization.py`, wire `covariance_method` through the existing strategy allocators, then build an in-memory sweep service/API that reuses the same allocator and engine path to generate summary metrics.

**Tech Stack:** Python 3.10, pandas, numpy, pytest, FastAPI, SQLAlchemy

---

### Task 1: Define covariance estimator behavior with failing tests

**Files:**
- Modify: `tests/core/test_optimization.py`
- Modify: `core/optimization.py`

**Step 1: Write the failing test**

Add tests that:

- verify `estimate_covariance(..., method="sample")` matches `returns.cov()`
- verify `ewma`, `shrinkage`, and `ensemble` outputs are symmetric, finite, and index-aligned
- verify `ensemble` differs from plain sample covariance on non-trivial return data

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_optimization.py -q`
Expected: FAIL because `estimate_covariance` does not exist yet.

**Step 3: Write minimal implementation**

Add the estimator function and use simple, well-bounded implementations for `sample`, `ewma`, `shrinkage`, and `ensemble`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_optimization.py -q`
Expected: PASS

### Task 2: Wire covariance_method through strategy allocators

**Files:**
- Modify: `backend/domain/backtest/service.py`
- Modify: `tests/api/test_backtest.py`

**Step 1: Write the failing test**

Add an API test that posts a backtest with `covariance_method="ensemble"` and verifies the service passes the parameter into the covariance estimation path.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because the parameter is ignored.

**Step 3: Write minimal implementation**

Parse `covariance_method` in allocator builders and replace direct `window_returns.cov()` calls with the shared estimator.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

### Task 3: Add a backtest sweep endpoint

**Files:**
- Modify: `backend/domain/backtest/service.py`
- Modify: `backend/domain/backtest/router.py`
- Modify: `tests/api/test_backtest.py`

**Step 1: Write the failing test**

Add an API test that posts a sweep request with multiple `lookback_days`, `rebalance_threshold`, and `covariance_method` values and expects multiple summary rows back.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because the endpoint or service does not exist yet.

**Step 3: Write minimal implementation**

Build an in-memory sweep helper that expands the grid, runs the backtests, and returns summary metrics.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

### Task 4: Verify repo health

**Step 1: Run focused checks**

Run:

- `python -m pytest tests/core/test_optimization.py -q`
- `python -m pytest tests/api/test_backtest.py -q`

Expected: PASS

**Step 2: Run full checks**

Run:

- `python -m pytest -q`
- `ruff check backend tests backtest examples`

Expected: PASS
