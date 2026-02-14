# Portfolio Dashboard Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Plotly Dash with a React frontend, wire Bloomberg data, add persistent portfolio storage, What-if sandbox, Stress Testing, and Bloomberg cache.

**Architecture:** New `backend/` directory (domain-driven FastAPI + SQLite) sits alongside untouched `core/` and `backtest/`. New `frontend/` directory (Vite + React + TypeScript + shadcn/ui). The old `dashboard/` is superseded but not deleted.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2, SQLite, xbbg, Pydantic v2, pytest/httpx · React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query, Recharts

---

## Phase 1 — Backend Foundation

### Task 1: Database models + session

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/database.py`
- Create: `backend/domain/__init__.py`

**Step 1: Create `backend/database.py`**

```python
"""SQLite database setup and session factory."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./portfolio.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    from backend.domain.portfolio.models import Portfolio, Position  # noqa: F401
    from backend.domain.market_data.models import MarketData  # noqa: F401
    from backend.domain.backtest.models import BacktestRun, BacktestResult  # noqa: F401
    from backend.domain.signals.models import Signal  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

**Step 2: Create empty `__init__.py` files**

```bash
# Create package markers
touch backend/__init__.py backend/domain/__init__.py
```

**Step 3: Commit**

```bash
git add backend/
git commit -m "feat(backend): add database module and package structure"
```

---

### Task 2: SQLAlchemy ORM models

**Files:**
- Create: `backend/domain/portfolio/__init__.py`
- Create: `backend/domain/portfolio/models.py`
- Create: `backend/domain/market_data/__init__.py`
- Create: `backend/domain/market_data/models.py`
- Create: `backend/domain/backtest/__init__.py`
- Create: `backend/domain/backtest/models.py`
- Create: `backend/domain/signals/__init__.py`
- Create: `backend/domain/signals/models.py`
- Test: `tests/domain/test_models.py`

**Step 1: Write failing test**

```python
# tests/domain/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.domain.portfolio.models import Portfolio, Position
from backend.domain.market_data.models import MarketData

@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()

def test_portfolio_creation(session):
    p = Portfolio(name="Test Fund", description="Demo")
    session.add(p)
    session.commit()
    assert session.query(Portfolio).count() == 1

def test_position_belongs_to_portfolio(session):
    p = Portfolio(name="Fund A")
    session.add(p)
    session.flush()
    pos = Position(portfolio_id=p.id, ticker="AAPL US Equity",
                   asset_class="Equity", quantity=100,
                   cost_price=150.0, currency="USD")
    session.add(pos)
    session.commit()
    assert session.query(Position).filter_by(portfolio_id=p.id).count() == 1

def test_market_data_upsert(session):
    from datetime import date
    md = MarketData(ticker="AAPL US Equity", date=date(2024, 1, 2),
                    close=185.5, source="bloomberg")
    session.add(md)
    session.commit()
    assert session.query(MarketData).first().close == 185.5
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/domain/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'backend'`

**Step 3: Create ORM models**

```python
# backend/domain/portfolio/models.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio",
                                                        cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), default="Equity")
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                  onupdate=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
```

```python
# backend/domain/market_data/models.py
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class MarketData(Base):
    __tablename__ = "market_data"
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_ticker_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="bloomberg")
    last_updated: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                    onupdate=func.now())
```

```python
# backend/domain/backtest/models.py
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    results: Mapped[list["BacktestResult"]] = relationship("BacktestResult",
                                                            back_populates="run",
                                                            cascade="all, delete-orphan")


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    run: Mapped["BacktestRun"] = relationship("BacktestRun", back_populates="results")
```

```python
# backend/domain/signals/models.py
from __future__ import annotations
from datetime import date
from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    signal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[str] = mapped_column(String(20), default="unknown")
```

**Step 4: Run tests**

```bash
pytest tests/domain/test_models.py -v
```
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add backend/ tests/domain/
git commit -m "feat(backend): add SQLAlchemy ORM models for all domains"
```

---

### Task 3: FastAPI app entry point + deps

**Files:**
- Create: `backend/deps.py`
- Create: `backend/main.py`

**Step 1: Create `backend/deps.py`**

```python
# backend/deps.py
"""Dependency injection providers."""
from __future__ import annotations
from typing import Generator
from sqlalchemy.orm import Session
from backend.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_bloomberg_client():
    """Return Bloomberg client, or None if unavailable (offline mode)."""
    try:
        from data.bloomberg_interface import BloombergInterface
        return BloombergInterface()
    except Exception:
        return None
```

**Step 2: Create `backend/main.py`**

```python
# backend/main.py
"""FastAPI application entry point."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables
from backend.domain.portfolio.router import router as portfolio_router
from backend.domain.market_data.router import router as market_data_router
from backend.domain.analytics.router import router as analytics_router
from backend.domain.signals.router import router as signals_router
from backend.domain.backtest.router import router as backtest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Portfolio Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router, prefix="/api")
app.include_router(market_data_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(backtest_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Step 3: Commit**

```bash
git add backend/deps.py backend/main.py
git commit -m "feat(backend): add FastAPI app entry point with CORS and deps"
```

---

## Phase 2 — Portfolio Domain

### Task 4: Portfolio CRUD + CSV import

**Files:**
- Create: `backend/domain/portfolio/service.py`
- Create: `backend/domain/portfolio/router.py`
- Create: `backend/schemas/portfolio.py`
- Test: `tests/api/test_portfolio.py`

**Step 1: Create Pydantic schemas**

```python
# backend/schemas/__init__.py  (empty)
# backend/schemas/portfolio.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    description: str = ""


class PortfolioRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    ticker: str
    asset_class: str = "Equity"
    quantity: float
    cost_price: float
    currency: str = "USD"


class PositionRead(PositionCreate):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}
```

**Step 2: Write failing API tests**

```python
# tests/api/test_portfolio.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.database import Base
from backend.deps import get_db

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_create_and_list_portfolio(client):
    r = client.post("/api/portfolios", json={"name": "Alpha Fund"})
    assert r.status_code == 201
    r2 = client.get("/api/portfolios")
    assert len(r2.json()) == 1
    assert r2.json()[0]["name"] == "Alpha Fund"


def test_add_position(client):
    pid = client.post("/api/portfolios", json={"name": "F"}).json()["id"]
    r = client.post(f"/api/portfolios/{pid}/positions",
                    json={"ticker": "AAPL US Equity", "quantity": 100, "cost_price": 150.0})
    assert r.status_code == 201


def test_csv_import(client):
    import io
    pid = client.post("/api/portfolios", json={"name": "F"}).json()["id"]
    csv_data = "ticker,quantity,cost_price,currency,asset_class\nAAPL US Equity,100,150.0,USD,Equity\n"
    r = client.post(f"/api/portfolios/{pid}/import-csv",
                    files={"file": ("holdings.csv", io.BytesIO(csv_data.encode()), "text/csv")})
    assert r.status_code == 200
    assert r.json()["imported"] == 1
```

**Step 3: Run test to verify failures**

```bash
pytest tests/api/test_portfolio.py -v
```
Expected: All FAIL (routers not yet created)

**Step 4: Create portfolio service**

```python
# backend/domain/portfolio/service.py
from __future__ import annotations
import csv
import io
from sqlalchemy.orm import Session
from backend.domain.portfolio.models import Portfolio, Position
from backend.schemas.portfolio import PortfolioCreate, PositionCreate


def list_portfolios(db: Session) -> list[Portfolio]:
    return db.query(Portfolio).all()


def create_portfolio(db: Session, data: PortfolioCreate) -> Portfolio:
    p = Portfolio(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def get_positions(db: Session, portfolio_id: int) -> list[Position]:
    return db.query(Position).filter_by(portfolio_id=portfolio_id).all()


def add_position(db: Session, portfolio_id: int, data: PositionCreate) -> Position:
    pos = Position(portfolio_id=portfolio_id, **data.model_dump())
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


def delete_position(db: Session, position_id: int) -> None:
    pos = db.query(Position).get(position_id)
    if pos:
        db.delete(pos)
        db.commit()


def import_csv(db: Session, portfolio_id: int, content: bytes) -> int:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    count = 0
    for row in reader:
        pos = Position(
            portfolio_id=portfolio_id,
            ticker=row["ticker"].strip(),
            quantity=float(row["quantity"]),
            cost_price=float(row["cost_price"]),
            currency=row.get("currency", "USD").strip(),
            asset_class=row.get("asset_class", "Equity").strip(),
        )
        db.add(pos)
        count += 1
    db.commit()
    return count
```

**Step 5: Create portfolio router**

```python
# backend/domain/portfolio/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.portfolio import service
from backend.schemas.portfolio import PortfolioCreate, PortfolioRead, PositionCreate, PositionRead

router = APIRouter(tags=["portfolio"])


@router.get("/portfolios", response_model=list[PortfolioRead])
def list_portfolios(db: Session = Depends(get_db)):
    return service.list_portfolios(db)


@router.post("/portfolios", response_model=PortfolioRead, status_code=201)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    return service.create_portfolio(db, data)


@router.get("/portfolios/{portfolio_id}/positions", response_model=list[PositionRead])
def get_positions(portfolio_id: int, db: Session = Depends(get_db)):
    return service.get_positions(db, portfolio_id)


@router.post("/portfolios/{portfolio_id}/positions", response_model=PositionRead, status_code=201)
def add_position(portfolio_id: int, data: PositionCreate, db: Session = Depends(get_db)):
    return service.add_position(db, portfolio_id, data)


@router.delete("/positions/{position_id}", status_code=204)
def delete_position(position_id: int, db: Session = Depends(get_db)):
    service.delete_position(db, position_id)


@router.post("/portfolios/{portfolio_id}/import-csv")
async def import_csv(portfolio_id: int, file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    try:
        count = service.import_csv(db, portfolio_id, content)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"imported": count}
```

**Step 6: Run tests**

```bash
pytest tests/api/test_portfolio.py -v
```
Expected: All PASSED

**Step 7: Commit**

```bash
git add backend/domain/portfolio/ backend/schemas/
git commit -m "feat(portfolio): CRUD endpoints + CSV import with tests"
```

---

## Phase 3 — Market Data Domain (Bloomberg Cache)

### Task 5: Bloomberg cache service + refresh endpoint

**Files:**
- Create: `backend/domain/market_data/service.py`
- Create: `backend/domain/market_data/router.py`
- Create: `backend/schemas/market_data.py`
- Test: `tests/domain/test_market_data_service.py`

**Step 1: Write failing test**

```python
# tests/domain/test_market_data_service.py
import pytest
from datetime import date
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.domain.market_data.models import MarketData
from backend.domain.market_data import service


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_get_prices_returns_empty_when_no_cache(session):
    result = service.get_cached_prices(session, "AAPL US Equity")
    assert result == []


def test_upsert_prices(session):
    rows = [{"date": date(2024, 1, 2), "close": 185.5, "volume": 1e6}]
    service.upsert_prices(session, "AAPL US Equity", rows)
    result = service.get_cached_prices(session, "AAPL US Equity")
    assert len(result) == 1
    assert result[0].close == 185.5


def test_bloomberg_unavailable_returns_cached(session):
    rows = [{"date": date(2024, 1, 2), "close": 100.0}]
    service.upsert_prices(session, "SPY US Equity", rows)
    # Bloomberg client is None (offline)
    updated = service.refresh_ticker(session, "SPY US Equity", bbg_client=None)
    assert updated == 0  # no new rows pulled


def test_bloomberg_pulls_incremental(session):
    # Pre-seed one row so last_updated is set
    rows = [{"date": date(2024, 1, 2), "close": 100.0}]
    service.upsert_prices(session, "SPY US Equity", rows)

    mock_bbg = MagicMock()
    import pandas as pd
    mock_df = pd.DataFrame({"SPY US Equity|PX_LAST": [101.0, 102.0]},
                           index=pd.to_datetime(["2024-01-03", "2024-01-04"]))
    mock_bbg.bdh.return_value = mock_df

    updated = service.refresh_ticker(session, "SPY US Equity", bbg_client=mock_bbg)
    assert updated == 2
```

**Step 2: Run to verify failures**

```bash
pytest tests/domain/test_market_data_service.py -v
```

**Step 3: Implement market data service**

```python
# backend/domain/market_data/service.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Any
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from backend.domain.market_data.models import MarketData


def get_cached_prices(db: Session, ticker: str) -> list[MarketData]:
    return db.query(MarketData).filter_by(ticker=ticker).order_by(MarketData.date).all()


def upsert_prices(db: Session, ticker: str, rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        stmt = (
            insert(MarketData)
            .values(ticker=ticker, date=row["date"], close=row["close"],
                    volume=row.get("volume"), source="bloomberg")
            .on_conflict_do_update(
                index_elements=["ticker", "date"],
                set_={"close": row["close"], "volume": row.get("volume")}
            )
        )
        db.execute(stmt)
        count += 1
    db.commit()
    return count


def get_last_date(db: Session, ticker: str) -> date | None:
    row = db.query(MarketData).filter_by(ticker=ticker).order_by(
        MarketData.date.desc()).first()
    return row.date if row else None


def refresh_ticker(db: Session, ticker: str, bbg_client: Any | None) -> int:
    """Pull incremental data from Bloomberg. Returns number of rows inserted."""
    if bbg_client is None:
        return 0
    last = get_last_date(db, ticker)
    start = (last + timedelta(days=1)).isoformat() if last else "2020-01-01"
    end = date.today().isoformat()
    if start > end:
        return 0
    try:
        df = bbg_client.bdh([ticker], ["PX_LAST"], start_date=start, end_date=end)
    except Exception:
        return 0
    if df.empty:
        return 0
    col = [c for c in df.columns if "PX_LAST" in c][0]
    rows = [{"date": idx.date(), "close": float(val)}
            for idx, val in df[col].items() if pd.notna(val)]
    return upsert_prices(db, ticker, rows)


def prices_to_returns(db: Session, tickers: list[str]) -> pd.DataFrame:
    """Build a returns DataFrame from cached prices for a list of tickers."""
    frames = {}
    for ticker in tickers:
        rows = get_cached_prices(db, ticker)
        if rows:
            s = pd.Series({r.date: r.close for r in rows}, name=ticker)
            frames[ticker] = s.pct_change().dropna()
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).dropna()
```

**Step 4: Create router**

```python
# backend/domain/market_data/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.deps import get_bloomberg_client, get_db
from backend.domain.market_data import service
from backend.domain.portfolio.models import Position

router = APIRouter(tags=["market_data"])


@router.get("/market-data/{ticker}")
def get_prices(ticker: str, db: Session = Depends(get_db)):
    rows = service.get_cached_prices(db, ticker)
    return [{"date": r.date.isoformat(), "close": r.close} for r in rows]


@router.post("/market-data/refresh")
def refresh_all(db: Session = Depends(get_db), bbg=Depends(get_bloomberg_client)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    total = sum(service.refresh_ticker(db, t, bbg) for t in tickers)
    online = bbg is not None
    return {"refreshed_rows": total, "online": online, "tickers": len(tickers)}
```

**Step 5: Run tests**

```bash
pytest tests/domain/test_market_data_service.py -v
```
Expected: All PASSED

**Step 6: Commit**

```bash
git add backend/domain/market_data/ backend/schemas/ tests/domain/test_market_data_service.py
git commit -m "feat(market-data): Bloomberg cache service with incremental refresh"
```

---

## Phase 4 — Analytics Domain

### Task 6: Risk + factor analytics endpoint

**Files:**
- Create: `backend/domain/analytics/__init__.py`
- Create: `backend/domain/analytics/service.py`
- Create: `backend/domain/analytics/router.py`
- Create: `backend/schemas/analytics.py`
- Test: `tests/domain/test_analytics_service.py`

**Step 1: Write failing test**

```python
# tests/domain/test_analytics_service.py
import pytest
import numpy as np
import pandas as pd
from backend.domain.analytics import service


@pytest.fixture()
def returns():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    tickers = ["A", "B", "C", "D"]
    data = np.random.randn(252, 4) * 0.01
    return pd.DataFrame(data, index=dates, columns=tickers)


@pytest.fixture()
def weights():
    return {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}


def test_compute_risk_returns_var(returns, weights):
    result = service.compute_risk(returns, weights)
    assert "var_95" in result
    assert 0 < result["var_95"] < 0.1


def test_compute_risk_returns_trc(returns, weights):
    result = service.compute_risk(returns, weights)
    assert "trc" in result
    assert set(result["trc"].keys()) == {"A", "B", "C", "D"}


def test_what_if_changes_var(returns, weights):
    base = service.compute_risk(returns, weights)
    adjusted = {"A": 0.1, "B": 0.1, "C": 0.4, "D": 0.4}
    result = service.compute_risk(returns, adjusted)
    assert result["var_95"] != base["var_95"]
```

**Step 2: Run to verify failures**

```bash
pytest tests/domain/test_analytics_service.py -v
```

**Step 3: Implement analytics service**

```python
# backend/domain/analytics/service.py
"""Analytics service — thin wrapper over core/ engines."""
from __future__ import annotations
import numpy as np
import pandas as pd
from core.risk_engine import (
    calculate_volatility,
    calculate_var_parametric,
    calculate_expected_shortfall,
    calculate_max_drawdown,
    calculate_marginal_risk_contribution,
    calculate_total_risk_contribution,
)
from core.factor_model import FactorModel


def compute_risk(returns: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Compute portfolio risk metrics from asset returns and weights."""
    if returns.empty or not weights:
        return {}

    # Align weights to returns columns
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}

    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()
    rets_aligned = returns[tickers].dropna()

    port_returns = rets_aligned @ w
    cov = rets_aligned.cov().values

    return {
        "volatility": float(calculate_volatility(port_returns)),
        "var_95": float(calculate_var_parametric(port_returns, confidence=0.95)),
        "es_95": float(calculate_expected_shortfall(port_returns, confidence=0.95)),
        "max_drawdown": float(calculate_max_drawdown(port_returns)),
        "trc": {
            t: float(v)
            for t, v in zip(tickers, calculate_total_risk_contribution(w, cov))
        },
        "correlation": {
            t: {t2: float(rets_aligned.corr().loc[t, t2]) for t2 in tickers}
            for t in tickers
        },
    }


def compute_nav(returns: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Compute NAV series and performance metrics."""
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}
    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()
    port_returns = (returns[tickers].dropna() @ w)
    nav = (1 + port_returns).cumprod()
    return {
        "nav": {d.isoformat(): float(v) for d, v in nav.items()},
        "total_return": float(nav.iloc[-1] - 1) if len(nav) else 0.0,
        "sharpe": float(port_returns.mean() / port_returns.std() * np.sqrt(252))
                  if port_returns.std() > 0 else 0.0,
    }
```

**Step 4: Create router**

```python
# backend/domain/analytics/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.analytics import service
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions

router = APIRouter(tags=["analytics"])


def _portfolio_data(portfolio_id: int, db: Session):
    positions = get_positions(db, portfolio_id)
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found")
    tickers = [p.ticker for p in positions]
    total_value = sum(p.quantity * p.cost_price for p in positions)
    weights = {p.ticker: (p.quantity * p.cost_price) / total_value for p in positions}
    returns = prices_to_returns(db, tickers)
    return weights, returns


@router.get("/portfolios/{portfolio_id}/analytics")
def get_analytics(portfolio_id: int, db: Session = Depends(get_db)):
    weights, returns = _portfolio_data(portfolio_id, db)
    return {**service.compute_nav(returns, weights), "weights": weights}


@router.get("/portfolios/{portfolio_id}/risk")
def get_risk(portfolio_id: int, db: Session = Depends(get_db)):
    weights, returns = _portfolio_data(portfolio_id, db)
    return service.compute_risk(returns, weights)


@router.post("/portfolios/{portfolio_id}/what-if")
def what_if(portfolio_id: int, body: dict, db: Session = Depends(get_db)):
    adjusted_weights: dict = body.get("adjusted_weights", {})
    _, returns = _portfolio_data(portfolio_id, db)
    return service.compute_risk(returns, adjusted_weights)
```

**Step 5: Run tests**

```bash
pytest tests/domain/test_analytics_service.py -v
```
Expected: All PASSED

**Step 6: Commit**

```bash
git add backend/domain/analytics/ tests/domain/test_analytics_service.py
git commit -m "feat(analytics): risk/NAV/what-if endpoints using core/ engines"
```

---

## Phase 5 — Signals, Stress Testing, Backtest

### Task 7: Signals + regime router

**Files:**
- Create: `backend/domain/signals/service.py`
- Create: `backend/domain/signals/router.py`

```python
# backend/domain/signals/service.py
from __future__ import annotations
import pandas as pd
from core.signals import compute_momentum, compute_mean_reversion, compute_vol_breakout
from core.regime_model import detect_regime


def compute_signals(returns: pd.DataFrame) -> dict:
    if returns.empty:
        return {}
    result = {}
    for ticker in returns.columns:
        s = returns[ticker]
        result[ticker] = {
            "momentum": float(compute_momentum(s)),
            "mean_reversion": float(compute_mean_reversion(s)),
            "vol_breakout": float(compute_vol_breakout(s)),
        }
    return result


def get_regime(returns: pd.DataFrame) -> dict:
    if returns.empty:
        return {"regime": "unknown", "confidence": 0.0}
    port_ret = returns.mean(axis=1)
    regime = detect_regime(port_ret)
    return {"regime": regime}
```

```python
# backend/domain/signals/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.signals import service
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.models import Position

router = APIRouter(tags=["signals"])


@router.get("/signals")
def get_signals(db: Session = Depends(get_db)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.compute_signals(returns)


@router.get("/signals/regime")
def get_regime(db: Session = Depends(get_db)):
    tickers = [t[0] for t in db.query(Position.ticker).distinct().all()]
    returns = prices_to_returns(db, tickers)
    return service.get_regime(returns)
```

**Step 1: Run basic smoke test**

```bash
uvicorn backend.main:app --reload
# Visit http://127.0.0.1:8000/api/health — should return {"status": "ok"}
```

**Step 2: Commit**

```bash
git add backend/domain/signals/
git commit -m "feat(signals): signals and regime endpoints"
```

---

### Task 8: Stress testing endpoint

**Files:**
- Create: `backend/domain/analytics/stress.py`
- Add route to: `backend/domain/analytics/router.py`

```python
# backend/domain/analytics/stress.py
"""Built-in stress test scenarios."""
from __future__ import annotations
import numpy as np

SCENARIOS: dict[str, dict[str, float]] = {
    "2008_gfc": {
        "description": "2008 Global Financial Crisis",
        "Equity": -0.50,
        "FixedIncome": 0.05,
        "Commodity": -0.30,
        "FX": -0.10,
        "Cash": 0.01,
    },
    "2020_covid": {
        "description": "2020 COVID Crash (Feb-Mar)",
        "Equity": -0.34,
        "FixedIncome": 0.08,
        "Commodity": -0.25,
        "FX": -0.05,
        "Cash": 0.01,
    },
    "2022_rate_shock": {
        "description": "2022 Rate Hike Cycle",
        "Equity": -0.20,
        "FixedIncome": -0.15,
        "Commodity": 0.20,
        "FX": 0.05,
        "Cash": 0.03,
    },
}


def run_scenario(
    positions: list,  # list of Position ORM objects
    scenario: dict[str, float],
) -> dict:
    total_value = sum(p.quantity * p.cost_price for p in positions)
    pnl = 0.0
    breakdown = {}
    for pos in positions:
        asset_class = pos.asset_class
        shock = scenario.get(asset_class, scenario.get("Equity", -0.20))
        pos_value = pos.quantity * pos.cost_price
        pos_pnl = pos_value * shock
        pnl += pos_pnl
        breakdown[pos.ticker] = {
            "shock_pct": shock,
            "pnl": round(pos_pnl, 2),
            "weight": round(pos_value / total_value, 4) if total_value else 0,
        }
    return {
        "total_pnl": round(pnl, 2),
        "pnl_pct": round(pnl / total_value, 4) if total_value else 0,
        "breakdown": breakdown,
    }
```

Add to `backend/domain/analytics/router.py`:

```python
from backend.domain.analytics.stress import SCENARIOS, run_scenario

@router.get("/stress-test/scenarios")
def list_scenarios():
    return [{"id": k, "description": v["description"]} for k, v in SCENARIOS.items()]

@router.post("/portfolios/{portfolio_id}/stress-test")
def stress_test(portfolio_id: int, body: dict, db: Session = Depends(get_db)):
    scenario_id = body.get("scenario_id")
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    positions = get_positions(db, portfolio_id)
    if not positions:
        raise HTTPException(status_code=404, detail="No positions")
    scenario = {k: v for k, v in SCENARIOS[scenario_id].items() if k != "description"}
    return run_scenario(positions, scenario)
```

**Step 1: Commit**

```bash
git add backend/domain/analytics/stress.py backend/domain/analytics/router.py
git commit -m "feat(analytics): stress testing with built-in historical scenarios"
```

---

### Task 9: Backtest domain

**Files:**
- Create: `backend/domain/backtest/service.py`
- Create: `backend/domain/backtest/router.py`

```python
# backend/domain/backtest/service.py
from __future__ import annotations
import json
import numpy as np
from sqlalchemy.orm import Session
from backtest.engine import BacktestEngine
from backtest.cost_model import LinearCostModel
from core.optimization import hierarchical_risk_parity
from backend.domain.backtest.models import BacktestRun, BacktestResult
from backend.domain.market_data.service import prices_to_returns
from backend.domain.portfolio.service import get_positions


STRATEGIES = {
    "hrp": hierarchical_risk_parity,
    "equal_weight": lambda r: dict(zip(r.columns, [1 / len(r.columns)] * len(r.columns))),
}


def run_backtest(db: Session, portfolio_id: int, params: dict) -> BacktestRun:
    strategy_name = params.get("strategy", "hrp")
    cost_bps = params.get("cost_bps", 10)
    lookback = params.get("lookback_days", 63)

    positions = get_positions(db, portfolio_id)
    tickers = [p.ticker for p in positions]
    returns = prices_to_returns(db, tickers)

    if returns.empty:
        raise ValueError("No market data cached for positions — refresh first")

    allocator_fn = STRATEGIES.get(strategy_name, hierarchical_risk_parity)
    cost_model = LinearCostModel(cost_bps / 10000)
    engine = BacktestEngine(returns, cost_model=cost_model, lookback=lookback)

    def allocator(window_returns):
        weights_dict = allocator_fn(window_returns)
        w = np.array([weights_dict.get(t, 0.0) for t in window_returns.columns])
        return w / w.sum() if w.sum() > 0 else w

    result = engine.run(allocator)

    run = BacktestRun(portfolio_id=portfolio_id, strategy=strategy_name,
                      params_json=json.dumps(params))
    db.add(run)
    db.flush()

    for date_idx, nav_val in result.nav.items():
        weights_on_date = result.weights.loc[date_idx].to_dict() if date_idx in result.weights.index else {}
        db.add(BacktestResult(run_id=run.id, date=date_idx.date(), nav=float(nav_val),
                              weights_json=json.dumps(weights_on_date)))
    db.commit()
    db.refresh(run)
    return run
```

```python
# backend/domain/backtest/router.py
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.deps import get_db
from backend.domain.backtest import service
from backend.domain.backtest.models import BacktestRun, BacktestResult

router = APIRouter(tags=["backtest"])


@router.post("/backtests", status_code=201)
def create_backtest(body: dict, db: Session = Depends(get_db)):
    portfolio_id = body.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id required")
    try:
        run = service.run_backtest(db, portfolio_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"run_id": run.id, "strategy": run.strategy}


@router.get("/backtests/{run_id}")
def get_backtest(run_id: int, db: Session = Depends(get_db)):
    run = db.query(BacktestRun).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    results = db.query(BacktestResult).filter_by(run_id=run_id).order_by(BacktestResult.date).all()
    return {
        "run_id": run.id,
        "strategy": run.strategy,
        "params": json.loads(run.params_json),
        "nav": [{"date": r.date.isoformat(), "nav": r.nav} for r in results],
    }


@router.get("/portfolios/{portfolio_id}/backtests")
def list_backtests(portfolio_id: int, db: Session = Depends(get_db)):
    runs = db.query(BacktestRun).filter_by(portfolio_id=portfolio_id).all()
    return [{"run_id": r.id, "strategy": r.strategy, "created_at": r.created_at.isoformat()}
            for r in runs]
```

**Step 1: Commit**

```bash
git add backend/domain/backtest/
git commit -m "feat(backtest): backtest domain with HRP and equal-weight strategies"
```

---

## Phase 6 — Update pyproject.toml

### Task 10: Register `backend` package

**File:** `pyproject.toml`

Change:
```toml
[tool.setuptools]
packages = ["core", "data", "backtest", "dashboard"]
```
To:
```toml
[tool.setuptools]
packages = ["core", "data", "backtest", "dashboard", "backend"]
```

Also update pytest coverage targets:
```toml
addopts = "-ra -q --cov=core --cov=backtest --cov=backend"
```

**Step 1: Run full backend test suite**

```bash
pytest tests/ -v
```
Expected: All domain and API tests pass.

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: register backend package and update test coverage config"
```

---

## Phase 7 — React Frontend

### Task 11: Scaffold Vite + React + shadcn/ui

**Step 1: Create project**

```bash
cd F:\Git\Multi-Asset-Portfolio-Intelligence-Allocation-Platform
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install dependencies**

```bash
npm install tailwindcss @tailwindcss/vite
npm install @tanstack/react-query axios zustand
npm install recharts
npm install react-router-dom
npm install lucide-react
npm install clsx tailwind-merge
```

**Step 3: Configure Tailwind (Vite plugin approach)**

Replace contents of `frontend/src/index.css`:
```css
@import "tailwindcss";
```

Update `frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

**Step 4: Initialize shadcn/ui**

```bash
npx shadcn@latest init
# Choose: Default style, Neutral base color, yes to CSS variables
```

**Step 5: Add core shadcn components**

```bash
npx shadcn@latest add button card table badge drawer select slider tabs
```

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Vite+React+TypeScript with shadcn/ui and Tailwind"
```

---

### Task 12: API client + global state

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/store.ts`
- Create: `frontend/src/lib/queryClient.ts`

**Step 1: Create API client**

```typescript
// frontend/src/lib/api.ts
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const portfolioApi = {
  list: () => api.get('/portfolios').then(r => r.data),
  create: (data: { name: string; description?: string }) =>
    api.post('/portfolios', data).then(r => r.data),
  getPositions: (id: number) => api.get(`/portfolios/${id}/positions`).then(r => r.data),
  addPosition: (id: number, data: object) =>
    api.post(`/portfolios/${id}/positions`, data).then(r => r.data),
  deletePosition: (id: number) => api.delete(`/positions/${id}`),
  importCsv: (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/portfolios/${id}/import-csv`, form).then(r => r.data)
  },
}

export const analyticsApi = {
  getAnalytics: (id: number) => api.get(`/portfolios/${id}/analytics`).then(r => r.data),
  getRisk: (id: number) => api.get(`/portfolios/${id}/risk`).then(r => r.data),
  getAttribution: (id: number) => api.get(`/portfolios/${id}/attribution`).then(r => r.data),
  whatIf: (id: number, weights: Record<string, number>) =>
    api.post(`/portfolios/${id}/what-if`, { adjusted_weights: weights }).then(r => r.data),
}

export const marketApi = {
  refresh: () => api.post('/market-data/refresh').then(r => r.data),
  getPrices: (ticker: string) => api.get(`/market-data/${ticker}`).then(r => r.data),
}

export const signalsApi = {
  getSignals: () => api.get('/signals').then(r => r.data),
  getRegime: () => api.get('/signals/regime').then(r => r.data),
}

export const stressApi = {
  getScenarios: () => api.get('/stress-test/scenarios').then(r => r.data),
  run: (portfolioId: number, scenarioId: string) =>
    api.post(`/portfolios/${portfolioId}/stress-test`, { scenario_id: scenarioId }).then(r => r.data),
}

export const backtestApi = {
  create: (data: object) => api.post('/backtests', data).then(r => r.data),
  get: (runId: number) => api.get(`/backtests/${runId}`).then(r => r.data),
  list: (portfolioId: number) => api.get(`/portfolios/${portfolioId}/backtests`).then(r => r.data),
}
```

**Step 2: Create Zustand store**

```typescript
// frontend/src/lib/store.ts
import { create } from 'zustand'

interface AppState {
  selectedPortfolioId: number | null
  setSelectedPortfolio: (id: number) => void
  whatIfWeights: Record<string, number>
  setWhatIfWeight: (ticker: string, weight: number) => void
  resetWhatIf: () => void
  isOnline: boolean
  setOnline: (v: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  selectedPortfolioId: null,
  setSelectedPortfolio: (id) => set({ selectedPortfolioId: id }),
  whatIfWeights: {},
  setWhatIfWeight: (ticker, weight) =>
    set((s) => ({ whatIfWeights: { ...s.whatIfWeights, [ticker]: weight } })),
  resetWhatIf: () => set({ whatIfWeights: {} }),
  isOnline: true,
  setOnline: (v) => set({ isOnline: v }),
}))
```

**Step 3: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat(frontend): add API client layer and Zustand global store"
```

---

### Task 13: App layout + routing

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Header.tsx`
- Modify: `frontend/src/main.tsx`

**Step 1: Create Layout with sidebar**

```tsx
// frontend/src/components/Layout.tsx
import { NavLink, Outlet } from 'react-router-dom'
import { BarChart2, AlertTriangle, Radio, RefreshCw, Settings, TrendingUp } from 'lucide-react'
import Header from './Header'

const nav = [
  { to: '/portfolio', icon: BarChart2, label: 'Portfolio' },
  { to: '/risk', icon: AlertTriangle, label: 'Risk' },
  { to: '/signals', icon: Radio, label: 'Signals' },
  { to: '/backtest', icon: TrendingUp, label: 'Backtest' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      <aside className="w-16 flex flex-col items-center py-6 gap-6 bg-zinc-900 border-r border-zinc-800">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} title={label}
            className={({ isActive }) =>
              `p-2 rounded-lg transition-colors ${isActive ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>
            <Icon size={20} />
          </NavLink>
        ))}
      </aside>
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

**Step 2: Create Header**

```tsx
// frontend/src/components/Header.tsx
import { useQuery, useMutation } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { portfolioApi, marketApi, signalsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

export default function Header() {
  const { selectedPortfolioId, setSelectedPortfolio, setOnline } = useAppStore()
  const { data: portfolios = [] } = useQuery({ queryKey: ['portfolios'], queryFn: portfolioApi.list })
  const { data: regime } = useQuery({ queryKey: ['regime'], queryFn: signalsApi.getRegime, refetchInterval: 60000 })

  const refresh = useMutation({
    mutationFn: marketApi.refresh,
    onSuccess: (data) => setOnline(data.online),
  })

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-zinc-900 border-b border-zinc-800">
      <div className="flex items-center gap-4">
        <span className="font-semibold text-sm text-zinc-300">Portfolio</span>
        <Select value={String(selectedPortfolioId ?? '')} onValueChange={(v) => setSelectedPortfolio(Number(v))}>
          <SelectTrigger className="w-48 h-8 bg-zinc-800 border-zinc-700 text-sm">
            <SelectValue placeholder="Select portfolio" />
          </SelectTrigger>
          <SelectContent>
            {portfolios.map((p: { id: number; name: string }) => (
              <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-3">
        {regime && (
          <Badge variant={regime.regime === 'risk_on' ? 'default' : 'destructive'} className="text-xs">
            {regime.regime === 'risk_on' ? '🟢 Risk-On' : '🔴 Risk-Off'}
          </Badge>
        )}
        <Button size="sm" variant="outline" className="h-8 text-xs border-zinc-700 bg-zinc-800"
          onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          <RefreshCw size={14} className={refresh.isPending ? 'animate-spin mr-1' : 'mr-1'} />
          Refresh Data
        </Button>
      </div>
    </header>
  )
}
```

**Step 3: Wire routing in App.tsx**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import Layout from './components/Layout'
import PortfolioPage from './pages/PortfolioPage'
import RiskPage from './pages/RiskPage'
import SignalsPage from './pages/SignalsPage'
import BacktestPage from './pages/BacktestPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/portfolio" replace />} />
            <Route path="portfolio" element={<PortfolioPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="signals" element={<SignalsPage />} />
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

```typescript
// frontend/src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})
```

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): app layout with sidebar navigation and header"
```

---

### Task 14: Portfolio page + What-if drawer

**Files:**
- Create: `frontend/src/pages/PortfolioPage.tsx`
- Create: `frontend/src/components/WhatIfDrawer.tsx`

**Step 1: Create Portfolio page**

```tsx
// frontend/src/pages/PortfolioPage.tsx
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Drawer, DrawerContent, DrawerTrigger } from '@/components/ui/drawer'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts'
import { analyticsApi, portfolioApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import WhatIfDrawer from '@/components/WhatIfDrawer'

export default function PortfolioPage() {
  const { selectedPortfolioId } = useAppStore()
  const [whatIfOpen, setWhatIfOpen] = useState(false)

  const { data: analytics } = useQuery({
    queryKey: ['analytics', selectedPortfolioId],
    queryFn: () => analyticsApi.getAnalytics(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  const { data: positions = [] } = useQuery({
    queryKey: ['positions', selectedPortfolioId],
    queryFn: () => portfolioApi.getPositions(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  if (!selectedPortfolioId) {
    return <div className="text-zinc-500 text-sm">Select a portfolio from the header to begin.</div>
  }

  const totalReturn = analytics?.total_return
  const sharpe = analytics?.sharpe
  const treemapData = positions.map((p: any) => ({
    name: p.ticker,
    size: p.quantity * p.cost_price,
    assetClass: p.asset_class,
  }))

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1"><CardTitle className="text-xs text-zinc-400">Total Return</CardTitle></CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalReturn != null ? `${(totalReturn * 100).toFixed(2)}%` : '—'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1"><CardTitle className="text-xs text-zinc-400">Sharpe Ratio</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{sharpe != null ? sharpe.toFixed(2) : '—'}</p></CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1"><CardTitle className="text-xs text-zinc-400">Positions</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{positions.length}</p></CardContent>
        </Card>
      </div>

      {/* Treemap */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Allocation</CardTitle>
          <Button size="sm" variant="outline" className="border-zinc-700 bg-zinc-800 text-xs h-7"
            onClick={() => setWhatIfOpen(true)}>What-if</Button>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <Treemap data={treemapData} dataKey="size" nameKey="name" stroke="#18181b"
              fill="#3f3f46">
              <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
            </Treemap>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Positions table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Positions</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800">
                <TableHead className="text-zinc-400 text-xs">Ticker</TableHead>
                <TableHead className="text-zinc-400 text-xs">Asset Class</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Quantity</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Cost Price</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p: any) => (
                <TableRow key={p.id} className="border-zinc-800 hover:bg-zinc-800/50">
                  <TableCell className="text-xs font-mono">{p.ticker}</TableCell>
                  <TableCell className="text-xs text-zinc-400">{p.asset_class}</TableCell>
                  <TableCell className="text-xs text-right">{p.quantity.toLocaleString()}</TableCell>
                  <TableCell className="text-xs text-right">${p.cost_price.toFixed(2)}</TableCell>
                  <TableCell className="text-xs text-right font-medium">
                    ${(p.quantity * p.cost_price).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <WhatIfDrawer open={whatIfOpen} onClose={() => setWhatIfOpen(false)}
        positions={positions} portfolioId={selectedPortfolioId} />
    </div>
  )
}
```

**Step 2: Create What-if drawer**

```tsx
// frontend/src/components/WhatIfDrawer.tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'
import { analyticsApi } from '@/lib/api'

interface Props {
  open: boolean
  onClose: () => void
  positions: any[]
  portfolioId: number
}

export default function WhatIfDrawer({ open, onClose, positions, portfolioId }: Props) {
  const totalValue = positions.reduce((s: number, p: any) => s + p.quantity * p.cost_price, 0)
  const initWeights: Record<string, number> = Object.fromEntries(
    positions.map((p: any) => [p.ticker, p.quantity * p.cost_price / totalValue])
  )
  const [weights, setWeights] = useState<Record<string, number>>(initWeights)
  const [result, setResult] = useState<any>(null)

  const whatIf = useMutation({
    mutationFn: () => analyticsApi.whatIf(portfolioId, weights),
    onSuccess: setResult,
  })

  return (
    <Drawer open={open} onClose={onClose} direction="right">
      <DrawerContent className="bg-zinc-900 border-zinc-800 w-80 right-0 left-auto">
        <DrawerHeader><DrawerTitle className="text-sm">What-if Sandbox</DrawerTitle></DrawerHeader>
        <div className="px-4 pb-4 space-y-4 overflow-y-auto">
          {positions.map((p: any) => (
            <div key={p.ticker}>
              <div className="flex justify-between text-xs text-zinc-400 mb-1">
                <span className="font-mono">{p.ticker}</span>
                <span>{((weights[p.ticker] ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <Slider min={0} max={1} step={0.01} value={[weights[p.ticker] ?? 0]}
                onValueChange={([v]) => setWeights(w => ({ ...w, [p.ticker]: v }))} />
            </div>
          ))}

          <Button size="sm" className="w-full" onClick={() => whatIf.mutate()} disabled={whatIf.isPending}>
            Calculate Impact
          </Button>

          {result && (
            <div className="space-y-2 pt-2 border-t border-zinc-800">
              <p className="text-xs text-zinc-400">Results</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-zinc-800 rounded p-2">
                  <p className="text-zinc-500">VaR 95%</p>
                  <p className="font-bold text-amber-400">{(result.var_95 * 100).toFixed(2)}%</p>
                </div>
                <div className="bg-zinc-800 rounded p-2">
                  <p className="text-zinc-500">Volatility</p>
                  <p className="font-bold">{(result.volatility * 100).toFixed(2)}%</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
```

**Step 3: Commit**

```bash
git add frontend/src/pages/PortfolioPage.tsx frontend/src/components/WhatIfDrawer.tsx
git commit -m "feat(frontend): portfolio page with positions table, treemap, and what-if drawer"
```

---

### Task 15: Risk page with stress test panel

**File:** `frontend/src/pages/RiskPage.tsx`

```tsx
// frontend/src/pages/RiskPage.tsx
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import { analyticsApi, stressApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

export default function RiskPage() {
  const { selectedPortfolioId } = useAppStore()
  const [scenarioId, setScenarioId] = useState<string>('')
  const [stressResult, setStressResult] = useState<any>(null)

  const { data: risk } = useQuery({
    queryKey: ['risk', selectedPortfolioId],
    queryFn: () => analyticsApi.getRisk(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })
  const { data: scenarios = [] } = useQuery({ queryKey: ['scenarios'], queryFn: stressApi.getScenarios })

  const runStress = useMutation({
    mutationFn: () => stressApi.run(selectedPortfolioId!, scenarioId),
    onSuccess: setStressResult,
  })

  if (!selectedPortfolioId) return <div className="text-zinc-500 text-sm">Select a portfolio.</div>

  const trcData = risk?.trc ? Object.entries(risk.trc).map(([k, v]) => ({ ticker: k, trc: Number(v) })) : []
  const corrData = risk?.correlation

  return (
    <div className="space-y-6">
      {/* Risk metric cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'VaR 95%', value: risk?.var_95, fmt: (v: number) => `${(v * 100).toFixed(2)}%`, color: 'text-amber-400' },
          { label: 'ES 95%', value: risk?.es_95, fmt: (v: number) => `${(v * 100).toFixed(2)}%`, color: 'text-orange-400' },
          { label: 'Volatility', value: risk?.volatility, fmt: (v: number) => `${(v * 100).toFixed(2)}%`, color: 'text-blue-400' },
          { label: 'Max Drawdown', value: risk?.max_drawdown, fmt: (v: number) => `${(v * 100).toFixed(2)}%`, color: 'text-red-400' },
        ].map(({ label, value, fmt, color }) => (
          <Card key={label} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-1"><CardTitle className="text-xs text-zinc-400">{label}</CardTitle></CardHeader>
            <CardContent><p className={`text-xl font-bold ${color}`}>{value != null ? fmt(value) : '—'}</p></CardContent>
          </Card>
        ))}
      </div>

      {/* TRC Chart */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Risk Contribution by Position</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={trcData} layout="vertical">
              <XAxis type="number" tick={{ fill: '#71717a', fontSize: 11 }} tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
              <YAxis type="category" dataKey="ticker" tick={{ fill: '#a1a1aa', fontSize: 11 }} width={100} />
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }} />
              <Bar dataKey="trc" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Stress Testing */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Stress Testing</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3 items-end">
            <Select value={scenarioId} onValueChange={setScenarioId}>
              <SelectTrigger className="w-64 bg-zinc-800 border-zinc-700 text-sm h-8">
                <SelectValue placeholder="Select scenario" />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map((s: any) => (
                  <SelectItem key={s.id} value={s.id}>{s.description}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" className="h-8" onClick={() => runStress.mutate()}
              disabled={!scenarioId || runStress.isPending}>Run</Button>
          </div>
          {stressResult && (
            <div className="space-y-2">
              <div className="flex gap-4">
                <div className="bg-zinc-800 rounded p-3">
                  <p className="text-xs text-zinc-500">Total P&L</p>
                  <p className={`text-lg font-bold ${stressResult.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${stressResult.total_pnl.toLocaleString()}
                  </p>
                </div>
                <div className="bg-zinc-800 rounded p-3">
                  <p className="text-xs text-zinc-500">P&L %</p>
                  <p className={`text-lg font-bold ${stressResult.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(stressResult.pnl_pct * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

**Step 1: Commit**

```bash
git add frontend/src/pages/RiskPage.tsx
git commit -m "feat(frontend): risk page with VaR cards, TRC chart, and stress test panel"
```

---

### Task 16: Signals, Backtest, Settings pages

**Files:**
- Create: `frontend/src/pages/SignalsPage.tsx`
- Create: `frontend/src/pages/BacktestPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`

**SignalsPage** — queries `/api/signals` and `/api/signals/regime`, renders a regime card and a table of per-asset signals (momentum, mean_reversion, vol_breakout), color-coded by sign.

**BacktestPage** — form with strategy selector (hrp/equal_weight), cost_bps input, lookback_days input. On submit, `POST /api/backtests`. Poll `GET /api/backtests/{run_id}` until result. Display NAV line chart (Recharts LineChart) and list of past runs.

**SettingsPage** — shows Bloomberg connection status (`GET /api/health` extended), last refresh time from market data, and a "Download CSV Template" button that generates the correct CSV headers inline.

Implement each as a straightforward React component following the same patterns as Portfolio/Risk pages. Commit each separately:

```bash
git commit -m "feat(frontend): signals page with regime card and signals table"
git commit -m "feat(frontend): backtest page with strategy config and NAV chart"
git commit -m "feat(frontend): settings page with Bloomberg status and CSV template"
```

---

## Final Verification

### Task 17: End-to-end smoke test

**Step 1: Start backend**
```bash
uvicorn backend.main:app --reload
```

**Step 2: Start frontend**
```bash
cd frontend && npm run dev
```

**Step 3: Manual walkthrough**
1. Open http://localhost:5173
2. Create a portfolio via the header + navigate to Settings to confirm DB created
3. Add one position manually, verify it appears in the table
4. Import the sample CSV (download template from Settings)
5. Click "Refresh Data" — verify Bloomberg status (online/offline badge)
6. Navigate to Risk — verify VaR card renders (even with cached/empty data it should show `—` not crash)
7. Run a stress test scenario — verify P&L breakdown appears
8. Navigate to Signals — verify regime card renders
9. Navigate to Backtest — submit an HRP run, verify NAV chart appears

**Step 4: Run full test suite**
```bash
pytest tests/ -v
```
Expected: All tests pass.

**Step 5: Final commit**
```bash
git add .
git commit -m "feat: complete portfolio dashboard redesign - React frontend + Bloomberg backend"
```
