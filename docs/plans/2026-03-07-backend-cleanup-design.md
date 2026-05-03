# Backend Cleanup And Demo Automation Design

**Date:** 2026-03-07

**Scope:** Clean high-value backend lint issues, make demo/example scripts part of automated validation, and remove pytest cache noise from the default repo workflow.

## Problem

The project is currently green on tests but still has three stability issues:

- Core backend router and service modules contain lint debt that makes future changes noisier and less trustworthy.
- Demo scripts are runnable by hand but not covered by automated tests, so drift can reappear unnoticed.
- Default pytest runs emit cache permission warnings due to inaccessible cache directories in this environment.

## Decision

Use a focused cleanup rather than a repo-wide formatting sweep:

- Refactor FastAPI router signatures to `Annotated[...]`-style dependencies and query parameters so Ruff no longer flags valid FastAPI patterns.
- Clean the backend files most relevant to current data/backtest workflows: database wiring, dependency injection, analytics router/service, backtest router/service, and market data router/service.
- Add automated tests that execute the demo/example scripts through real Python subprocesses and assert successful completion without stderr noise.
- Disable pytest's cache provider in repo defaults to avoid environment-specific cache directory permission warnings. Also ignore transient pytest cache directories in repo scanning.

## Rationale

- `Annotated[...]` keeps FastAPI idioms explicit and tool-friendly without adding `noqa` clutter.
- Targeted cleanup improves maintainability where current work is concentrated, without wasting time on unrelated historical lint debt.
- Running the scripts as subprocesses verifies the true CLI entrypoint behavior, not just helper functions.
- Disabling cache provider is a pragmatic repo-level fix because the underlying directory permission problem is environmental, not application logic.

## Validation

- `ruff check` passes for the touched backend modules and new demo tests.
- `python -m pytest -q` passes without pytest cache warnings.
- `python tests/run_demo.py` succeeds.
- Automated tests confirm both `tests/run_demo.py` and `examples/backtest_example.py` execute successfully.
