# Multi-Asset Portfolio Intelligence & Allocation Platform
 
**Status**: Production / Institutional-Grade  
**Version**: 0.1.0  
**License**: MIT
 
A professional Python platform for multi-asset monitoring, factor risk modeling, robust optimization, tactical allocation, and institutional reporting. Designed for Quants and Portfolio Managers.
 
---
 
## 🚀 Key Features
 
### 1. **Advanced Analytics Core**
- **Risk Engine**: Parametric VaR (Gaussian), Expected Shortfall (CVaR), Total & Marginal Risk Contribution (TRC/MRC).
- **Performance Metrics**: Max Drawdown, Calmar Ratio, Sortino Ratio, Information Ratio.
- **Factor Model**: Rolling OLS exposures, Factor Covariance with Ledoit-Wolf shrinkage, Specific Risk decomposition.
- **Attribution**: Multi-period Brinson-Fachler attribution with Carino smoothing.
 
### 2. **Robust Optimization**
- **Hierarchical Risk Parity (HRP)**: Machine learning-based allocation using clustering (Single Linkage) and recursive bisection.
- **Risk Budgeting**: Equal Risk Contribution (ERC) and Target Risk Contribution constraints.
- **Mean-Variance**: Classic MVO with constraints (Long-only, Max weight).
 
### 3. **Institutional Dashboard**
- **Interactive UI**: Fully responsive **Dark Mode** Plotly Dash interface.
- **Live Updates**: Callback-driven architecture for real-time data refreshing.
- **Modules**:
  - **Portfolio Overview**: NAV, Treemap allocation, Rolling Returns.
  - **Risk & Factors**: Correlation Heatmap, Factor Exposures, Beta/Duration.
  - **Optimization**: Efficient Frontier visualization, Weight/Budget comparison.
  - **Macro Intelligence**: Yield Curves, Credit Spreads, Regime Signals.
 
### 4. **Production Engineering**
- **Backtesting**: Walk-forward engine with **Transaction Cost** modeling (bps), turnover tracking, and optional drift-threshold rebalancing.
- **Architecture**: Modular `src` layout with Dependency Injection (FastAPI `Depends`).
- **Quality**: Full `pytest` suite, Type hinting (`mypy`), and `pydantic` schemas.
 
---
 
## 🛠️ System Architecture
 
```text
[Data Layer]                 [Core Analytics]                  [Application Layer]
Bloomberg (xbbg)    --->     FactorModel (OLS/PCA)      --->   REST API (FastAPI)
SQLAlchemy (DB)     --->     RiskEngine (VaR/CVaR)      --->   Dashboard (Dash)
Parquet Cache       --->     Optimizer (HRP/MVO)        --->   Jupyter Notebooks
                             BacktestEngine (Costs)
```
 
---
 
## 📦 Installation
 
```bash
# Clone the repository
git clone https://github.com/your-repo/multi-asset-platform.git
cd multi-asset-platform
 
# Install with dependencies
pip install -e .
 
# (Optional) Install dev dependencies for testing
pip install -e .[dev]
```
 
---
 
## 🚦 Usage
 
### 1. Run the Dashboard
Launch the full-stack application (FastAPI backend + Dash frontend):
 
```bash
uvicorn dashboard.backend.main:app --reload
```
Open **[http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)** in your browser.
 
> **Windows Users**: You can double-click `run_dashboard.bat` to automatically install dependencies and start the dashboard if Python is installed in a standard location.
 
### 2. Run Integration Demo
Verify the pipeline (Data -> Factor Model -> HRP Optimization -> Backtest):
 
```bash
python tests/run_demo.py
```
 
### 3. Run Tests
Execute the unit test suite:
 
```bash
python -m pytest
```

### 4. Research Backtests
Use the walk-forward engine directly when you want to study execution assumptions:

```python
engine = BacktestEngine(rebalance_freq="ME")
result = engine.run(
    returns,
    allocator=my_allocator,
    lookback=252,
    cost_bps=10.0,
    rebalance_threshold=0.05,
)

turnover = result.turnover
transaction_costs = result.transaction_costs
```

`rebalance_threshold` is optional. When set, the engine still computes target weights on scheduled rebalance dates but only trades when the drift versus current weights is large enough to justify turnover.

Backtests launched through the API also accept `covariance_method` for covariance-sensitive strategies:

- `sample`
- `ewma`
- `shrinkage`
- `ensemble`

Backtests launched through the API also support an optional regime-aware exposure overlay:

- `regime_overlay`: enable the overlay heuristic, for example `trend`
- `risk_on_exposure`: target gross exposure in risk-on conditions
- `risk_off_exposure`: target gross exposure in risk-off conditions
- `benchmark_regime_overlay`: optional benchmark flag, default `false`

For research sweeps, use `POST /api/backtests/sweep` with parameter grids such as `lookback_days_grid`, `cost_bps_grid`, `rebalance_threshold_grid`, `covariance_method_grid`, `regime_overlay_grid`, `risk_on_exposure_grid`, and `risk_off_exposure_grid`. The response returns one summary row per parameter combination, including return, volatility, drawdown, turnover, and transaction-cost metrics.

When a backtest is configured with a benchmark, `GET /api/backtests/{run_id}` now also returns a `relative_attribution` block with benchmark-relative summary metrics and a daily series of active return and active share.
 
---
 
## 📂 Project Structure
 
```text
.
├── core/                   # Quantitative Core
│   ├── attribution.py      # Brinson & Multi-period attribution
│   ├── factor_model.py     # Risk model estimation
│   ├── optimization.py     # HRP, MVO, Black-Litterman
│   ├── portfolio.py        # Portfolio state & accounting
│   ├── risk_budgeting.py   # ERC/TRC solvers
│   ├── risk_engine.py      # VaR, Drawdown, Ratios
│   └── signals.py          # Momentum, Carry, Volatility signals
├── data/                   # Data Engineering
│   ├── bloomberg_interface.py
│   └── database.py
├── backtest/               # Simulation
│   ├── engine.py           # Walk-forward loop
│   └── cost_model.py       # Transaction costs
├── dashboard/              # UI/UX
│   ├── backend/            # FastAPI Routes & Services
│   └── frontend/           # Plotly Dash App (Dark Mode)
├── tests/                  # Test Suite
├── pyproject.toml          # Dependencies & Build Config
└── README.md               # Documentation
```
