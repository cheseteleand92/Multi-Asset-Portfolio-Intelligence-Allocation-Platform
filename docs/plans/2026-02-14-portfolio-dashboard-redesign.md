# Portfolio Dashboard Redesign — Design Document

**Date:** 2026-02-14
**Status:** Approved
**Scope:** Full redesign of frontend + backend API layer; core analytics preserved

---

## Context

The existing platform has a solid quantitative core (`core/`, `backtest/`) but uses Plotly Dash for the frontend and serves synthetic data. This redesign replaces the frontend with React and wires up real Bloomberg data, persistent portfolio storage, and three new capability modules: What-if sandbox, Stress Testing, and Bloomberg data caching.

**Constraints:**
- Single user, runs locally
- Bloomberg Terminal as primary data source (xbbg/blpapi)
- Holdings input via CSV import or manual entry
- No automation — monitoring primary, signals + backtest as secondary
- Mixed assets (equities dominant)

---

## Architecture

```
frontend/  (React + Vite + TypeScript)
  shadcn/ui + Tailwind + Zustand + TanStack Query + Recharts
        │
        │  REST API (JSON) — http://localhost:8000/api
        │
backend/  (FastAPI + SQLite)
  domain/portfolio, market_data, analytics, signals, backtest
  core/, backtest/  ← unchanged
```

**Dev startup:**
```bash
uvicorn backend.main:app --reload   # :8000
cd frontend && npm run dev           # :5173
```

---

## Backend Structure

```
backend/
├── main.py
├── database.py              # SQLite + SQLAlchemy session
├── deps.py                  # DI: DB session, Bloomberg client
├── domain/
│   ├── portfolio/           # Holdings CRUD, CSV import
│   ├── market_data/         # Bloomberg wrapper + cache layer
│   ├── analytics/           # Calls core/ — risk, factor, attribution
│   ├── signals/             # Calls core/signals + regime_model
│   └── backtest/            # Calls backtest/, persists results
└── schemas/                 # Pydantic v2 request/response models
```

---

## Data Model (SQLite)

| Table | Key Columns |
|-------|-------------|
| `portfolios` | id, name, description, created_at |
| `positions` | id, portfolio_id, ticker, asset_class, quantity, cost_price, currency, updated_at |
| `market_data` | ticker, date, close, volume, source, last_updated |
| `factor_exposures` | portfolio_id, date, factor, exposure |
| `backtest_runs` | id, portfolio_id, strategy, params_json, created_at |
| `backtest_results` | run_id, date, nav, weights_json, metrics_json |
| `signals` | ticker, date, signal_type, value, regime |

Bloomberg prices are cached in `market_data`. Refresh is manual (button-triggered), pulling only incremental data since `last_updated`.

---

## API Endpoints

```
# Portfolio
GET    /api/portfolios
POST   /api/portfolios
GET    /api/portfolios/{id}/positions
POST   /api/portfolios/{id}/positions
POST   /api/portfolios/{id}/import-csv
DELETE /api/positions/{id}

# Market Data
GET    /api/market-data/{ticker}
POST   /api/market-data/refresh

# Analytics
GET    /api/portfolios/{id}/analytics       # NAV, returns, metrics
GET    /api/portfolios/{id}/risk            # VaR, ES, factor, TRC
GET    /api/portfolios/{id}/attribution     # Brinson multi-period
POST   /api/portfolios/{id}/what-if         # Sandbox: adjusted weights → risk delta

# Signals & Macro
GET    /api/signals
GET    /api/signals/regime

# Stress Testing
GET    /api/stress-test/scenarios
POST   /api/portfolios/{id}/stress-test

# Backtest
POST   /api/backtests
GET    /api/backtests/{run_id}
GET    /api/portfolios/{id}/backtests
```

**What-if contract:**
```json
// POST /api/portfolios/{id}/what-if
// Request: { "adjusted_weights": {"AAPL": 0.15, "SPY": 0.30} }
// Response: { "var_95": 0.021, "factor_exposures": {...}, "risk_contributions": {...} }
```

---

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/portfolio` | NAV card, Treemap allocation, positions table, **What-if drawer** |
| `/risk` | VaR/ES/drawdown cards, correlation heatmap, factor bar chart, TRC pie, **stress test panel** |
| `/signals` | Regime card, per-asset signal table, macro panel (yields, spreads, FX) |
| `/backtest` | Param config panel, NAV curve, rolling Sharpe, drawdown, historical runs table |
| `/settings` | Bloomberg connection status, cache management, CSV template download |

**Global header:** Portfolio selector dropdown, "Refresh Market Data" button, Regime status badge.

**What-if UX:** Right-side drawer on `/portfolio`. Weight sliders per position, real-time POST to `/what-if`, displays risk delta vs current.

---

## Three Key Additions

### 1. What-if Sandbox
Adjust position weights in a drawer UI, see real-time impact on VaR, factor exposures, and risk contributions. State is temporary (Zustand only), never persisted.

### 2. Stress Testing
Built-in historical scenarios: 2008 GFC, 2020 COVID, 2022 rate shock. Custom scenario support (e.g., "Equity -15%, Rates +100bps"). Shows expected P&L vs current VaR for context.

### 3. Bloomberg Data Cache
All market prices cached in SQLite. Manual "Refresh" button triggers incremental Bloomberg pull. Offline mode (uses cache) shown with yellow indicator in header.

---

## Error Handling

- Bloomberg unavailable → offline mode, yellow header badge, all views use cached data
- Insufficient data for calculation → component-level empty state with reason, page stays functional
- CSV import error → return specific row/field errors, display as list in UI

**Required CSV format:**
```
ticker, quantity, cost_price, currency, asset_class
AAPL, 100, 150.00, USD, Equity
```

---

## Testing

- `tests/core/` — existing unit tests, unchanged
- `tests/domain/` — new: domain service business logic
- `tests/api/` — new: FastAPI route integration tests (httpx)
- Frontend — no automated tests (single-user local tool)
