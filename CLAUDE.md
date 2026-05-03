# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in development mode with all dev dependencies
pip install -e .[dev]

# Run the full application (FastAPI + Dash on http://127.0.0.1:8000)
uvicorn dashboard.backend.main:app --reload

# Tests
python -m pytest                            # full suite with coverage
python -m pytest tests/core/test_risk_engine.py  # single file
python -m pytest -v                         # verbose

# Integration demo (full pipeline: data → factor model → HRP → backtest)
python tests/run_demo.py

# Linting and formatting
black .
ruff check .
mypy .
```

## Architecture

The platform is a layered quant stack:

```
[data/]  →  [core/]  →  [backtest/]  →  [dashboard/]
```

- **`data/`** — Data ingestion: Bloomberg wrapper (`bloomberg_interface.py`), SQLAlchemy ORM (`database.py`), caching layer (`cache_manager.py`). Bloomberg is optional; the dashboard uses synthetic data by default via `DashboardDataService`.

- **`core/`** — Pure-Python analytics. Each module is independent and stateless except `portfolio.py` (Portfolio state container). Key modules:
  - `factor_model.py` — OLS rolling exposures, Ledoit-Wolf covariance shrinkage, specific variance
  - `risk_engine.py` — VaR/ES, drawdown, Sharpe/Sortino/Calmar/Info ratios, MRC/TRC decomposition
  - `optimization.py` — MVO (CVXPY/SCS), HRP (SciPy hierarchical clustering + recursive bisection), Black-Litterman
  - `risk_budgeting.py` — ERC/TRC solvers with long-only and vol-target constraints
  - `attribution.py` — Brinson-Fachler single-period; multi-period with Carino smoothing
  - `signals.py` / `regime_model.py` — Momentum/carry/mean-reversion signals, risk-on/off classifier

- **`backtest/`** — Walk-forward backtester (`engine.py`) that accepts any allocator callable, tracks turnover, and applies linear transaction costs (bps).

- **`dashboard/backend/`** — FastAPI app (`main.py`) mounts:
  - `/api/dashboard` — Bundle endpoint returning all analytics in one call
  - `/portfolio`, `/risk`, `/factor`, `/optimization`, `/macro`, `/signals` — Individual REST endpoints
  - `/dashboard` — Plotly Dash WSGI app (dark-mode, interactive charts)

  The `DashboardDataService` singleton (created via `@lru_cache` in `dependencies.py`) generates synthetic market data and wires all core analytics for dashboard consumption. All responses are typed as Pydantic v2 schemas in `dashboard/backend/schemas/api.py`.

## Key Conventions

- **Python ≥ 3.10** required; all modules use full type hints (mypy strict).
- CVXPY with the SCS solver is used for constrained optimization — avoid adding solver dependencies without checking compatibility.
- The Dash frontend is mounted as a WSGI sub-application inside FastAPI; changes to the Dash layout live in `dashboard/frontend/app.py`.
- `conftest.py` in `tests/` provides shared fixtures (sample returns DataFrame, covariance matrix, weight Series) — reuse these rather than generating ad-hoc test data.
- No CI/CD pipeline exists yet; lint/type-check/test must be run manually.
