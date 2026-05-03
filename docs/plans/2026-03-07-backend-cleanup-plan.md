# Backend Cleanup And Demo Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make backend entrypoint code cleaner to maintain, bring demo scripts under automated verification, and remove pytest cache permission noise from default test runs.

**Architecture:** Keep behavior stable while refactoring FastAPI router signatures and service helpers into lint-compliant shapes. Add subprocess-based demo tests so the verified behavior is the same path users execute from the command line. Adjust pytest and repo ignore settings so environment-specific cache directories do not pollute the default workflow.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy, pytest, Ruff

---

### Task 1: Clean backend router and service lint issues

**Files:**
- Modify: `backend/database.py`
- Modify: `backend/deps.py`
- Modify: `backend/domain/analytics/router.py`
- Modify: `backend/domain/analytics/service.py`
- Modify: `backend/domain/backtest/router.py`
- Modify: `backend/domain/backtest/service.py`
- Modify: `backend/domain/market_data/router.py`
- Modify: `backend/domain/market_data/service.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

Use Ruff on the targeted backend files.

**Step 2: Run test to verify it fails**

Run:

```bash
ruff check backend/database.py backend/deps.py backend/domain/analytics/router.py backend/domain/analytics/service.py backend/domain/backtest/router.py backend/domain/backtest/service.py backend/domain/market_data/router.py backend/domain/market_data/service.py
```

Expected: import-order, FastAPI parameter, exception-chaining, and line-length failures.

**Step 3: Write minimal implementation**

- Convert router parameter signatures to `typing.Annotated`.
- Chain raised `HTTPException` instances from caught exceptions where needed.
- Refactor long service expressions into smaller helpers or wrapped statements.
- Update Ruff configuration only where it improves tool compatibility, not to suppress real issues.

**Step 4: Run test to verify it passes**

Run the same Ruff command and confirm zero failures.

**Step 5: Commit**

```bash
git add backend/database.py backend/deps.py backend/domain/analytics/router.py backend/domain/analytics/service.py backend/domain/backtest/router.py backend/domain/backtest/service.py backend/domain/market_data/router.py backend/domain/market_data/service.py pyproject.toml
git commit -m "refactor: clean backend router and service quality issues"
```

### Task 2: Add automated verification for demo scripts

**Files:**
- Create: `tests/test_demo_scripts.py`
- Modify: `tests/run_demo.py`
- Modify: `examples/backtest_example.py`

**Step 1: Write the failing test**

Create tests that execute both scripts via `subprocess.run(...)` and assert:

- exit code `0`
- expected success text in stdout
- empty stderr

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_demo_scripts.py -q
```

Expected: fail if either script still imports stale APIs, emits runtime warnings, or exits non-zero.

**Step 3: Write minimal implementation**

- Fix any remaining script drift or warning-producing logic.
- Keep scripts simple entrypoints.

**Step 4: Run test to verify it passes**

Run the same pytest command and confirm pass.

**Step 5: Commit**

```bash
git add tests/test_demo_scripts.py tests/run_demo.py examples/backtest_example.py
git commit -m "test: automate verification for demo scripts"
```

### Task 3: Remove pytest cache noise from default runs

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Step 1: Write the failing test**

Use the current default suite output as the failure condition.

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest -q
```

Expected: `PytestCacheWarning` due to inaccessible cache directories.

**Step 3: Write minimal implementation**

- Disable pytest cache provider in default repo config.
- Ignore transient pytest cache directories in repo scanning.

**Step 4: Run test to verify it passes**

Run `python -m pytest -q` again and confirm the cache warning is gone.

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "chore: remove pytest cache noise from default workflow"
```
