# Multi-Asset Portfolio Intelligence & Allocation Platform

Production-grade Python platform for institutional multi-asset monitoring, factor risk modeling, optimization, tactical allocation, and backtesting with Bloomberg integration.

## Step 1: System Architecture & Data Flow

```text
[ Bloomberg Terminal/API ]
        |  (BDH / BDP / BDS / ECO / Curves / FX)
        v
+-------------------------+
| data.bloomberg_interface|
+-------------------------+
        |
        +--> [data.cache_manager] --> Parquet cache
        |
        +--> [data.database] SQLAlchemy ORM (positions, trades, factors, risk, signals, benchmarks)
        |
        v
+-------------------- CORE ANALYTICS LAYER --------------------+
| core.portfolio      core.factor_model     core.risk_engine   |
| core.signals        core.regime_model     core.attribution   |
| core.optimization   core.risk_budgeting                      |
+--------------------------------------------------------------+
        |
        +--> [backtest.engine + cost_model + performance]
        |
        +--> [dashboard.backend FastAPI + embedded Dash]
```

### Data Flow
1. Bloomberg wrapper fetches market/reference/membership/macro/curve data.
2. Data is cached and persisted in SQL database.
3. Core analytics compute exposures, covariance, risk decomposition, signals, and optimized allocations.
4. Backtest engine validates allocation logic via walk-forward simulation.
5. FastAPI serves `/api/dashboard` and embeds the Dash UI at `/dashboard` for a single-entrypoint deployment.

## Step 2: Folder Structure

```text
core/
  portfolio.py
  risk_engine.py
  factor_model.py
  optimization.py
  risk_budgeting.py
  attribution.py
  signals.py
  regime_model.py

data/
  bloomberg_interface.py
  cache_manager.py
  database.py

backtest/
  engine.py
  cost_model.py
  performance.py

dashboard/
  backend/main.py
  frontend/app.py

examples/
  optimization_example.py
  backtest_example.py
```

- `core/`: portfolio math, factor model, risk decomposition, optimization, and tactical signal logic.
- `data/`: Bloomberg ingestion, caching, and SQLAlchemy ORM schema.
- `backtest/`: walk-forward framework with cost and performance modules.
- `dashboard/`: FastAPI service and embedded Dash institutional dashboard.
- `examples/`: runnable reference workflows.

## Step 3: Bloomberg Interface Wrapper

Implemented in `data/bloomberg_interface.py` with:
- xbbg primary backend.
- blpapi fallback initialization.
- Methods for `bdh`, `bdp`, `bds`, `eco`, `yield_curve`, `fx_spot_forward`.
- normalized DataFrame output and logging.

## Step 4: FactorModel Class

Implemented in `core/factor_model.py` with:
- rolling OLS exposure estimation.
- shrinkage factor covariance (Ledoit-Wolf optional).
- specific variance estimation.
- portfolio variance decomposition:

\[
\text{Var}_p = w^\top B F B^\top w + w^\top D w
\]

- outputs include factor/specific shares and total variance.

## Step 5: RiskBudgetingEngine Class

Implemented in `core/risk_budgeting.py` with cvxpy-based:
- TRC solver (target risk contribution).
- ERC solver (equal risk contribution).
- constraints: long-only, max weight, volatility target.
- optional turnover and transaction cost penalties.

## Step 6: Sample Optimization Example

See `examples/optimization_example.py`:
- synthetic expected returns/covariance generation.
- mean-variance allocation.
- ERC allocation via risk budgeting.
- printed institutional-style allocation summary.

Run:

```bash
python examples/optimization_example.py
```

## Step 7: Example Backtest Script

See `examples/backtest_example.py`:
- synthetic multi-asset return panel.
- monthly walk-forward rebalance.
- allocator using mean-variance optimizer.
- final NAV, annualized return, annualized vol outputs.

Run:

```bash
python examples/backtest_example.py
```

## Step 8: Setup Instructions

### Requirements
- Python 3.10+
- Bloomberg terminal session + `xbbg` or `blpapi`

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pandas numpy scipy scikit-learn cvxpy sqlalchemy fastapi uvicorn dash plotly xbbg blpapi
```

### Initialize DB

```python
from data.database import create_session
SessionLocal = create_session("sqlite:///portfolio.db")
```

### Run the Full Dashboard Stack (single command)

```bash
uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8000
```

Then open:
- API health: `http://localhost:8000/health`
- Dashboard API payload: `http://localhost:8000/api/dashboard`
- Institutional dashboard UI: `http://localhost:8000/dashboard`

## Notes for Production Hardening
- Replace sample dashboard payload with live pipeline output from core risk/optimization/backtest engines.
- Add secure secret management and Bloomberg entitlement checks.
- Add robust blpapi request/response parser for non-xbbg environments.
- Add CI tests with stochastic seeds and deterministic fixtures.
- Add portfolio constraints by asset class, region, factor, and tracking-error budget.
- Add stress scenario library (rate shock, equity crash, FX devaluation).
