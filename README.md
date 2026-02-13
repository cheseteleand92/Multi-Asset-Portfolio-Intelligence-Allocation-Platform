# Multi-Asset Portfolio Intelligence & Allocation Platform

Production-grade Python platform for multi-asset monitoring, factor risk modeling, optimization, tactical allocation, market intelligence, backtesting, and an institutional dashboard. Bloomberg (`xbbg` / `blpapi`) is the primary data interface.

## Step 1: System Architecture & Data Flow Diagram

```text
Bloomberg Terminal/API
 (BDH/BDP/BDS/ECO/Curves/FX/Fundamentals)
            |
            v
+---------------------------+
| data.bloomberg_interface  |
+---------------------------+
      |                |
      |                +--> data.cache_manager (parquet cache)
      v
+---------------------------+
| data.database (SQLAlchemy)|
| positions/trades/snapshots|
| factors/risk/signals/bench|
+---------------------------+
      |
      v
+------------------------------ CORE -----------------------------+
| portfolio | factor_model | risk_engine | risk_budgeting        |
| optimization | attribution | signals | regime_model            |
+---------------------------------------------------------------+-+
                                                                |
                  +---------------------------------------------+------------------+
                  |                                                                |
                  v                                                                v
        backtest.engine/cost/perf                                     dashboard.backend (FastAPI)
                                                                              |   REST endpoints
                                                                              v
                                                                  dashboard.frontend (Dash)
                                                                  /dashboard institutional UI
```

## Step 2: Folder Structure + Explanation

```text
core/
  portfolio.py            # holdings, NAV, active weights
  factor_model.py         # rolling regression multi-factor model
  risk_engine.py          # vol/TE/VaR/ES/risk contribution helpers
  risk_budgeting.py       # ERC/TRC with cvxpy + constraints
  optimization.py         # MVO + Black-Litterman utilities
  attribution.py          # Brinson-style attribution
  signals.py              # momentum/carry signal utilities
  regime_model.py         # regime classification

data/
  bloomberg_interface.py  # Bloomberg BDH/BDP/BDS/ECO wrapper
  cache_manager.py        # parquet cache
  database.py             # SQLAlchemy ORM schema

backtest/
  engine.py               # walk-forward engine
  cost_model.py           # transaction/slippage models
  performance.py          # drawdown/sharpe metrics

dashboard/
  backend/main.py
  backend/routes/         # /portfolio /risk /factor /optimization /macro /signals
  backend/schemas/        # Pydantic response models
  backend/services/       # payload orchestration service
  frontend/app.py         # full Dash UI (5 mandatory pages)

examples/
  optimization_example.py
  backtest_example.py
```

## Step 3: Database Schema Models

Implemented in `data/database.py` using SQLAlchemy ORM:
- `Position`
- `Trade`
- `PortfolioSnapshot`
- `FactorExposure`
- `HistoricalRisk`
- `SignalHistory`
- `BenchmarkReturn`

`create_session()` initializes schema and returns a session factory.

## Step 4: Bloomberg API Wrapper Class

Implemented in `data/bloomberg_interface.py`:
- xbbg-first initialization and blpapi fallback bootstrap.
- `bdh()`, `bdp()`, `bds()`, `eco()`, `yield_curve()`, `fx_spot_forward()`.
- normalized pandas DataFrame outputs for downstream analytics.

## Step 5: FactorModel Class Implementation

Implemented in `core/factor_model.py`:
- rolling OLS exposure estimation (`estimate_exposures`).
- factor covariance with optional Ledoit-Wolf shrinkage (`estimate_factor_covariance`).
- specific variance estimation (`estimate_specific_variance`).
- variance decomposition:

\[
\mathrm{Var}(p)=w^\top B F B^\top w + w^\top D w
\]

where:
- \(B\): factor exposures,
- \(F\): factor covariance,
- \(D\): diagonal specific-risk matrix.

## Step 6: RiskBudgetingEngine Implementation

Implemented in `core/risk_budgeting.py` with cvxpy.

Supported:
- ERC and TRC
- risk caps per asset (`max_weight`)
- factor exposure caps (`factor_risk_caps`)
- regional cap (`regional_risk_caps`)
- tracking-error constraint (`tracking_error_limit`)
- volatility target (`vol_target`)
- turnover penalty
- transaction-cost penalty

Outputs:
- optimal weights
- marginal risk contribution table
- total risk contribution table

Formulas:

\[
RC_i = w_i(\Sigma w)_i, \quad MRC_i = \frac{(\Sigma w)_i}{\sigma_p}
\]

## Step 7: Optimization Example

`examples/optimization_example.py` includes:
- synthetic expected return + covariance,
- mean-variance solution,
- ERC allocation with risk contribution diagnostics.

Run:

```bash
python examples/optimization_example.py
```

## Step 8: Backtest Example

`examples/backtest_example.py` includes:
- walk-forward monthly rebalance,
- optimizer-based allocator,
- NAV and annualized performance summary.

Run:

```bash
python examples/backtest_example.py
```

## Step 9: FULL Dashboard Backend Implementation

FastAPI backend in `dashboard/backend/main.py` with modular routes:
- `GET /portfolio`
- `GET /risk`
- `GET /factor`
- `GET /optimization`
- `GET /macro`
- `GET /signals`

Additional:
- `GET /api/dashboard` for full bundled payload
- `GET /health`
- Pydantic schemas under `dashboard/backend/schemas/api.py`
- SQLAlchemy schema available in `data/database.py`

## Step 10: FULL Dashboard Frontend Implementation

Dash frontend in `dashboard/frontend/app.py` includes all mandatory pages/charts:
1. Portfolio Overview
   - NAV
   - Allocation treemap
   - Rolling return
   - Risk contribution
2. Risk & Factor
   - Factor exposure table
   - Factor risk contribution
   - Correlation heatmap
   - Beta exposure
   - Duration exposure
3. Optimization
   - Efficient frontier
   - Weight comparison
   - Risk budget visualization
   - Constraint impact visualization
4. TAA / Regime
   - Regime probability
   - Signal dashboard
   - Suggested allocation shift
5. Macro Intelligence
   - Yield curve
   - Credit spread
   - FX index
   - Volatility index
   - Scenario shock result

## Step 11: Setup Instructions

### Requirements
- Python 3.10+
- Bloomberg Terminal entitlements
- `xbbg` or `blpapi`

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

### Run Full Stack

```bash
uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8000
```

Open:
- `http://localhost:8000/dashboard`
- `http://localhost:8000/portfolio`
- `http://localhost:8000/risk`
- `http://localhost:8000/factor`
- `http://localhost:8000/optimization`
- `http://localhost:8000/macro`
- `http://localhost:8000/signals`
- `http://localhost:8000/api/dashboard`
