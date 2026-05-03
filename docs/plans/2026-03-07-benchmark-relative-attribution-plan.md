# Benchmark-Relative Backtest Attribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose benchmark-relative diagnostics directly in the backtest detail API so research users can evaluate active risk and active positioning without external post-processing.

**Architecture:** Rebuild the benchmark as a full backtest result, align it with the stored strategy run, and compute relative summary and date-level metrics in the backtest service. The router will expose the result in a dedicated `relative_attribution` response block.

**Tech Stack:** Python 3.10, pandas, pytest, FastAPI, SQLAlchemy

---

### Task 1: Define relative attribution response behavior with failing tests

**Files:**
- Modify: `tests/api/test_backtest.py`
- Modify: `backend/domain/backtest/service.py`
- Modify: `backend/domain/backtest/router.py`

**Step 1: Write the failing test**

Add tests that:

- verify a benchmarked backtest detail response includes `relative_attribution.summary`
- verify the summary includes active return, tracking error, information ratio, max relative drawdown, and average active share
- verify `relative_attribution` is `None` when benchmark is `none`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: FAIL because the response does not include the new block.

**Step 3: Write minimal implementation**

Build benchmark results with weights, compute aligned relative metrics, and attach the block to the detail response.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_backtest.py -q`
Expected: PASS

### Task 2: Verify repo health

**Step 1: Run targeted checks**

Run:

- `python -m pytest tests/api/test_backtest.py -q`

Expected: PASS

**Step 2: Run full checks**

Run:

- `python -m pytest -q`
- `ruff check backend tests backtest core examples`

Expected: PASS
