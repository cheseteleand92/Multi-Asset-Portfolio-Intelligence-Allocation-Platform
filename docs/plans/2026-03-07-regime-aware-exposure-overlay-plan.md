# Regime-Aware Exposure Overlay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let research backtests scale total exposure in risk-on vs risk-off regimes without changing the underlying allocator logic.

**Architecture:** Wrap the existing strategy allocator with a regime-aware exposure scaler driven by the current regime heuristic in the signals service. Keep the overlay optional and disabled by default, and avoid applying it to benchmarks unless explicitly requested.

**Tech Stack:** Python 3.10, pandas, pytest, FastAPI

---

### Task 1: Define overlay behavior with failing tests

**Files:**
- Modify: `tests/api/test_backtest.py`
- Modify: `backend/domain/backtest/service.py`

**Step 1: Write the failing test**

Add a test that:

- forces the regime classifier to report `risk_off`
- runs a strategy and benchmark backtest with the same equal-weight allocator
- verifies the strategy weights are scaled to `risk_off_exposure`
- verifies the benchmark remains fully invested

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because the overlay parameters are ignored.

**Step 3: Write minimal implementation**

Wrap the strategy allocator with an exposure overlay and leave benchmarks unwrapped by default.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

### Task 2: Verify repo health

**Step 1: Run focused checks**

Run:

- `python -m pytest tests/api/test_backtest.py -q`

Expected: PASS

**Step 2: Run full checks**

Run:

- `python -m pytest -q`
- `ruff check backend tests backtest core examples`

Expected: PASS
