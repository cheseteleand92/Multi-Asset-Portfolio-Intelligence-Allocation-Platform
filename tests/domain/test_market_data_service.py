from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.domain.market_data import service


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
