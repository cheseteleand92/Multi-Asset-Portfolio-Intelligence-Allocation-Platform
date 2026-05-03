import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.domain.market_data.models import MarketData
from backend.domain.portfolio.models import Portfolio, Position


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
