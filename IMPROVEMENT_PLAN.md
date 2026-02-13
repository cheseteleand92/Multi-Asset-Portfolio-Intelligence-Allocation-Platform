# Multi-Asset Portfolio Intelligence Platform — Professional Improvement Plan

## Executive Summary

Current state: ~844 lines of Python across 27 files. The architecture skeleton is sound (layered
design, separation of concerns), but most modules are **skeletal stubs** with minimal logic.
To reach institutional/production quality, the platform needs significant depth in analytics,
robustness in engineering, and completeness in infrastructure.

Below is a prioritized, phased plan covering **7 major workstreams** and **42 specific action items**.

---

## Phase 1: Engineering Foundation (Priority: Critical)

### 1.1 Package & Dependency Management
- **Problem**: No `requirements.txt`, no `pyproject.toml`, no `__init__.py` in any package directory.
  The project cannot be installed or imported reliably.
- **Actions**:
  - [ ] Create `pyproject.toml` with proper metadata, dependencies, and optional extras
        (`[dev]`, `[bloomberg]`, `[dashboard]`)
  - [ ] Add `__init__.py` to `core/`, `data/`, `backtest/`, `dashboard/`, `dashboard/backend/`,
        `dashboard/backend/routes/`, `dashboard/backend/schemas/`, `dashboard/backend/services/`,
        `dashboard/frontend/`
  - [ ] Add `.gitignore` (Python, IDE, `.cache/`, `*.db`, `__pycache__/`)
  - [ ] Add `.env.example` with documented environment variables

### 1.2 Testing Infrastructure
- **Problem**: Zero test coverage. No `tests/` directory. No validation of any analytics.
- **Actions**:
  - [ ] Create `tests/` directory with `conftest.py` containing shared fixtures
        (synthetic returns, covariance matrices, sample portfolios)
  - [ ] Unit tests for every core module:
    - `test_portfolio.py` — normalization, active weights, NAV computation
    - `test_factor_model.py` — OLS regression correctness, decomposition identity
      (factor_var + specific_var = total_var)
    - `test_risk_engine.py` — VaR/ES bounds, MRC/TRC summing to portfolio vol
    - `test_risk_budgeting.py` — ERC solution produces equal risk contributions,
      constraint satisfaction
    - `test_optimization.py` — MVO feasibility, Black-Litterman posterior correctness
    - `test_attribution.py` — Brinson decomposition sums to active return
    - `test_signals.py` — momentum/carry signal shape and sign
    - `test_regime_model.py` — output is binary 0/1
  - [ ] Integration tests for backtest engine (end-to-end with known expected output)
  - [ ] API tests using FastAPI `TestClient` for all 6 endpoints + health
  - [ ] Add `pytest.ini` or `[tool.pytest.ini_options]` in pyproject.toml

### 1.3 CI/CD & Containerization
- **Actions**:
  - [ ] `Dockerfile` + `docker-compose.yml` (API + PostgreSQL + Redis)
  - [ ] `.github/workflows/ci.yml`: lint (ruff), type-check (mypy), test (pytest),
        coverage report
  - [ ] Pre-commit hooks config (`.pre-commit-config.yaml`): ruff, mypy, black

---

## Phase 2: Core Analytics Deepening (Priority: High)

### 2.1 Risk Engine Enhancement (`core/risk_engine.py` — currently 39 lines)
- **Problem**: Only has basic VaR/ES and MRC/TRC. Missing many institutional-standard metrics.
- **Actions**:
  - [ ] Add **Parametric VaR** (Gaussian) and **Cornish-Fisher VaR** (skew/kurtosis adjusted)
  - [ ] Add **Component VaR** (CVaR decomposition by asset)
  - [ ] Add **Incremental VaR** (impact of adding a position)
  - [ ] Add **Stress VaR** / scenario-based VaR
  - [ ] Add **Max Drawdown**, **Calmar Ratio**, **Sortino Ratio**, **Information Ratio**
  - [ ] Add **Tracking Error** calculation (ex-ante and ex-post)
  - [ ] Add **Beta** calculation vs benchmark
  - [ ] Annualization should be configurable (252 trading days vs 365)

### 2.2 Factor Model Enhancement (`core/factor_model.py` — currently 152 lines)
- **Problem**: Only rolling OLS with Ledoit-Wolf. No WLS, no robust regression, no PCA factors.
- **Actions**:
  - [ ] Add **WLS (Weighted Least Squares)** with exponential decay for recency bias
  - [ ] Add **PCA-based statistical factor extraction** as alternative to fundamental factors
  - [ ] Add **Newey-West HAC standard errors** for exposure significance testing
  - [ ] Add **R-squared and adjusted R-squared** per asset to flag poor factor coverage
  - [ ] Add **Factor VIF (Variance Inflation Factor)** to detect multicollinearity
  - [ ] Add **Rolling factor stability** tracking (exposure change over time)

### 2.3 Attribution Enhancement (`core/attribution.py` — currently 21 lines)
- **Problem**: Only single-period Brinson. No multi-period, no factor-based, no fixed-income.
- **Actions**:
  - [ ] Add **Multi-period Brinson** (with compounding / smoothing, e.g., Carino method)
  - [ ] Add **Factor-based attribution** (decompose returns into factor tilts * factor returns)
  - [ ] Add **Currency attribution** for multi-currency portfolios (local return + FX return)
  - [ ] Add **Fixed-income attribution** (carry, roll-down, spread change, curve shift)

### 2.4 Signals & Regime Enhancement (`core/signals.py` 14 lines, `core/regime_model.py` 11 lines)
- **Problem**: Extremely thin — only 2 signals and 1 binary rule-based regime.
- **Actions**:
  - [ ] Add **Mean-reversion signal** (z-score based)
  - [ ] Add **Volatility breakout signal** (realized vs implied vol ratio)
  - [ ] Add **Macro surprise signal** (economic data surprise index)
  - [ ] Add **Sentiment / positioning signal** framework
  - [ ] Replace rule-based regime with **Hidden Markov Model (HMM)** for regime detection
        (2-state or 3-state: risk-on / risk-off / crisis)
  - [ ] Add **Markov regime-switching probabilities** and transition matrix estimation

### 2.5 Optimization Enhancement (`core/optimization.py` — currently 48 lines)
- **Problem**: Only basic MVO and Black-Litterman. No robust optimization, no resampling.
- **Actions**:
  - [ ] Add **Resampled Efficient Frontier** (Michaud resampling)
  - [ ] Add **Robust optimization** (uncertainty sets on expected returns)
  - [ ] Add **CVaR optimization** (minimize conditional value-at-risk)
  - [ ] Add **Maximum Diversification** portfolio
  - [ ] Add **Hierarchical Risk Parity (HRP)** (Lopez de Prado)
  - [ ] Add **Min Tracking Error** optimization
  - [ ] Add **multi-period / dynamic** optimization stub

---

## Phase 3: Data Layer Robustness (Priority: High)

### 3.1 Bloomberg Interface (`data/bloomberg_interface.py`)
- **Problem**: `blpapi` fallback is `NotImplementedError` for all methods. No data validation.
- **Actions**:
  - [ ] Implement `blpapi` fallback for `bdh()`, `bdp()`, `bds()` methods
  - [ ] Add data validation (missing values, stale data detection, weekend/holiday filtering)
  - [ ] Add rate limiting and retry logic for Bloomberg API calls
  - [ ] Add **data quality checks**: NaN ratio thresholds, price staleness alerts

### 3.2 Cache Manager (`data/cache_manager.py` — currently 25 lines)
- **Problem**: No TTL, no cache invalidation, no concurrent access safety.
- **Actions**:
  - [ ] Add TTL-based cache expiration
  - [ ] Add `has()` method and `delete()` method
  - [ ] Add metadata tracking (last updated timestamp, row count)
  - [ ] Add optional Redis backend for distributed caching

### 3.3 Database Layer (`data/database.py`)
- **Problem**: Schema is defined but nothing writes to or reads from it. No repository layer.
- **Actions**:
  - [ ] Create `data/repository.py` with CRUD operations for each table
  - [ ] Add bulk upsert for positions and snapshots (for daily batch ingestion)
  - [ ] Add migration support via Alembic
  - [ ] Add connection pooling configuration
  - [ ] Switch default from SQLite to PostgreSQL for production

---

## Phase 4: Backtest Engine Enhancement (Priority: Medium)

### 4.1 Backtest Engine (`backtest/engine.py` — currently 49 lines)
- **Problem**: Monthly-only rebalancing, no cost integration, no slippage, no multi-portfolio.
- **Actions**:
  - [ ] Support configurable rebalancing frequencies (daily, weekly, monthly, quarterly)
  - [ ] Integrate `cost_model.py` into the backtest loop (deduct costs from returns)
  - [ ] Add **slippage model** (market impact based on trade size / ADV)
  - [ ] Add **cash drag** modeling (uninvested cash earns risk-free rate)
  - [ ] Add **weight drift** tracking between rebalances
  - [ ] Add **rebalance trigger** options (calendar-based, threshold-based, signal-based)
  - [ ] Add **multi-strategy** backtesting (run multiple allocators, compare)

### 4.2 Performance Module (`backtest/performance.py` — currently 18 lines)
- **Problem**: Only rolling Sharpe and drawdown. Missing standard performance metrics.
- **Actions**:
  - [ ] Add **CAGR** (compound annual growth rate)
  - [ ] Add **Sortino Ratio**, **Calmar Ratio**, **Omega Ratio**
  - [ ] Add **Maximum Drawdown duration** (time-to-recovery)
  - [ ] Add **Turnover analysis** (annualized turnover, cost drag)
  - [ ] Add **Performance summary table** (standardized output dataclass)
  - [ ] Add **Benchmark-relative metrics** (alpha, beta, information ratio, up/down capture)

---

## Phase 5: Dashboard & API Professionalization (Priority: Medium)

### 5.1 API Architecture Issues
- **Problem**: Each route file creates its own `DashboardDataService()` instance (7 separate
  instances total). No dependency injection, no caching, no error handling.
- **Actions**:
  - [ ] Use FastAPI `Depends()` for dependency injection of a single shared service instance
  - [ ] Add proper error handling middleware (structured error responses)
  - [ ] Add request/response logging middleware
  - [ ] Add API versioning (`/api/v1/...`)
  - [ ] Add authentication & authorization (API key or JWT)
  - [ ] Add rate limiting
  - [ ] Restrict CORS origins (currently allows `*` — security risk)

### 5.2 Dashboard Frontend (`dashboard/frontend/app.py`)
- **Problem**: Static data rendered once at startup. No callbacks, no interactivity, no styling.
- **Actions**:
  - [ ] Add Dash **callbacks** for dynamic date range filtering
  - [ ] Add portfolio selector dropdown (multi-portfolio support)
  - [ ] Add auto-refresh (periodic polling or WebSocket-based live updates)
  - [ ] Add **dark theme** / professional institutional styling (CSS)
  - [ ] Add **data download** buttons (CSV/Excel export)
  - [ ] Add drill-down capability (click asset → see position detail)
  - [ ] Improve chart formatting (proper date axes, tooltips, legends)

### 5.3 Data Service (`dashboard/backend/services/data_service.py`)
- **Problem**: 100% hardcoded synthetic data. Not connected to any real data source.
- **Actions**:
  - [ ] Connect to actual database (read from Position, PortfolioSnapshot, etc.)
  - [ ] Connect to Bloomberg interface for live market data
  - [ ] Add caching layer (avoid re-computing factor model on every request)
  - [ ] Add date-range parameterization (not just "latest snapshot")

---

## Phase 6: Advanced Features (Priority: Lower)

### 6.1 Execution & Trade Management
- **Actions**:
  - [ ] Add `core/execution.py`: order generation from target vs current weights
  - [ ] Add trade list generation with rounding to lot sizes
  - [ ] Add pre-trade compliance checks (weight limits, restricted list)
  - [ ] Add post-trade reconciliation logic

### 6.2 Currency Hedging Module
- **Actions**:
  - [ ] Add `core/currency.py`: FX exposure calculation by holding currency
  - [ ] Add hedge ratio optimization (full hedge, partial hedge, cost-aware)
  - [ ] Add FX forward roll cost estimation

### 6.3 Stress Testing & Scenario Analysis
- **Actions**:
  - [ ] Add `core/stress_testing.py`: historical scenario replay
        (GFC 2008, COVID 2020, rate shock, etc.)
  - [ ] Add parametric stress testing (shift curves, widen spreads)
  - [ ] Add reverse stress testing (what breaks the portfolio?)

### 6.4 Reporting & Compliance
- **Actions**:
  - [ ] Add PDF report generation (investment committee deck)
  - [ ] Add guideline compliance engine (configurable rules)
  - [ ] Add breach alerting system

---

## Phase 7: Code Quality & Operational Concerns (Priority: Ongoing)

### 7.1 Type Safety & Linting
- **Actions**:
  - [ ] Add `py.typed` marker and run `mypy --strict` on all modules
  - [ ] Replace `Dict[str, object]` with proper TypedDict or Pydantic models throughout
  - [ ] Add `ruff` configuration for consistent style enforcement

### 7.2 Logging & Observability
- **Problem**: Only `bloomberg_interface.py` uses logging. All other modules are silent.
- **Actions**:
  - [ ] Add structured logging (JSON format) throughout all modules
  - [ ] Add request tracing (correlation IDs)
  - [ ] Add performance metrics (optimization solve time, data fetch latency)
  - [ ] Add health check depth (DB connectivity, Bloomberg connectivity, cache status)

### 7.3 Configuration Management
- **Actions**:
  - [ ] Create centralized `config.py` using Pydantic `BaseSettings`
        (reads from environment variables and `.env` files)
  - [ ] All magic numbers (252 trading days, default risk aversion, etc.)
        should be configurable
  - [ ] Add environment profiles (dev / staging / production)

---

## Prioritized Implementation Order

| Priority | Phase | Estimated Scope | Impact |
|----------|-------|-----------------|--------|
| P0 | 1.1 Package management | `pyproject.toml`, `__init__.py`, `.gitignore` | Can't run without this |
| P0 | 1.2 Testing | `tests/` with core module unit tests | Analytics correctness |
| P1 | 2.1 Risk engine depth | VaR variants, drawdown, ratios | Core value proposition |
| P1 | 2.3 Attribution | Multi-period Brinson, factor attribution | Key differentiator |
| P1 | 2.5 Optimization | HRP, CVaR opt, robust methods | Professional-grade |
| P1 | 3.3 Database layer | Repository pattern, Alembic | Persistent data |
| P2 | 2.2 Factor model | WLS, PCA, significance tests | Analytical depth |
| P2 | 2.4 Signals & regime | HMM, additional signals | TAA quality |
| P2 | 4.1 Backtest engine | Cost integration, multi-freq | Realistic backtests |
| P2 | 5.1 API architecture | DI, error handling, auth | Production readiness |
| P3 | 5.2 Dashboard | Callbacks, styling, drill-down | User experience |
| P3 | 1.3 CI/CD | Docker, GitHub Actions | DevOps maturity |
| P3 | 4.2 Performance metrics | Full metric suite | Reporting |
| P4 | 6.x Advanced features | Execution, FX, stress test | Institutional completeness |
| P4 | 7.x Code quality | Typing, logging, config | Long-term maintenance |

---

## Critical Bugs & Issues Found During Review

1. **`portfolio.py:28`** — `normalize_weights()` checks `abs().sum() == 0` but divides by
   `sum()` (not `abs().sum()`). If weights sum to 0 but have non-zero entries (e.g., `+0.5, -0.5`),
   this causes division by zero.

2. **`risk_engine.py:12`** — `portfolio_volatility()` returns non-annualized volatility
   (despite docstring claiming "annualized"). Missing `* np.sqrt(252)`.

3. **`backtest/engine.py:33`** — `resample().last()` on a DatetimeIndex may produce unexpected
   rebalance dates. Should use `pd.offsets` for precise month-end alignment.

4. **API route duplication** — Each of the 6 route files instantiates its own
   `DashboardDataService()`, causing the synthetic factor model to be re-fitted 7+ times per
   dashboard load (once per route + once in `main.py`).

5. **`main.py:48`** — `_dash = create_dashboard_app(service.get_payload())` is called at
   module import time, meaning the Dash app is frozen at server startup and never updates.

6. **`data_service.py:38`** — `np.random.seed(1)` is called in a method, which means every
   call returns identical data. This is fine for synthetic mode but will be confusing when
   transitioning to real data.

7. **No `__init__.py`** in any package — relative imports will fail; the project is not
   installable as a Python package.

8. **`black_litterman_posterior`** — Uses `np.linalg.inv()` on potentially singular matrices
   without any regularization or fallback.

---

*Plan generated: 2026-02-13*
*Total action items: 42 workstreams across 7 phases*
