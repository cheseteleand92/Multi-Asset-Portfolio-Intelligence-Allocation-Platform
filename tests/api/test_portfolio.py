import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.database import Base
from backend.deps import get_db

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
