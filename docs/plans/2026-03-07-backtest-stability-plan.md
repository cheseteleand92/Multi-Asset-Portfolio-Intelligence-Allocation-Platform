# Backtest Stability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the backtest engine invest on the first eligible day and align repo test guidance with the working Python invocation.

**Architecture:** Keep the existing walk-forward engine shape and adjust only the rebalance trigger logic. Lock the new semantics with focused regression tests, then update the local project guidance so contributors run the suite through the same interpreter as the application code.

**Tech Stack:** Python 3.10, pandas, pytest, FastAPI docs/guidance files

---

### Task 1: Lock the desired initialization behavior with tests

**Files:**
- Modify: `tests/backtest/test_engine.py`
- Modify: `backtest/engine.py`

**Step 1: Write the failing test**

Add assertions that:

- weights sum to `0.0` before `lookback` is available
- weights sum to `1.0` from the first eligible day onward
- the first eligible day uses the allocator output immediately

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: FAIL in `test_backtest_run_monthly` because the engine stays in cash until the first scheduled rebalance date.

**Step 3: Write minimal implementation**

Adjust `BacktestEngine.run` so the first eligible date initializes weights immediately, while subsequent rebalances still honor the configured schedule.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/backtest/test_engine.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/backtest/test_engine.py backtest/engine.py
git commit -m "fix(backtest): invest on first eligible rebalance day"
```

### Task 2: Align local guidance with the working test command

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Step 1: Write the failing test**

Use the existing investigation result as the failure condition: repo guidance currently recommends `pytest`, which proved less reliable than `python -m pytest` in this environment.

**Step 2: Run test to verify it fails**

Run: `Get-Content README.md` and `Get-Content CLAUDE.md`
Expected: See `pytest` examples without the explicit `python -m` prefix.

**Step 3: Write minimal implementation**

Update the documented test commands to use `python -m pytest`, preserving the same example targets.

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: align test commands with active Python environment"
```
