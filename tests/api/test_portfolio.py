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


def test_update_position(client):
    pid = client.post("/api/portfolios", json={"name": "F"}).json()["id"]
    created = client.post(
        f"/api/portfolios/{pid}/positions",
        json={
            "ticker": "AAPL US Equity",
            "quantity": 100,
            "cost_price": 150.0,
            "currency": "USD",
            "asset_class": "Equity",
        },
    ).json()

    update = client.put(
        f"/api/positions/{created['id']}",
        json={
            "ticker": "MSFT US Equity",
            "quantity": 120,
            "cost_price": 300.0,
            "currency": "USD",
            "asset_class": "Equity",
        },
    )

    assert update.status_code == 200
    payload = update.json()
    assert payload["ticker"] == "MSFT US Equity"
    assert payload["quantity"] == 120


def test_csv_import_replace(client):
    import io

    pid = client.post("/api/portfolios", json={"name": "F"}).json()["id"]
    client.post(
        f"/api/portfolios/{pid}/positions",
        json={
            "ticker": "AAPL US Equity",
            "quantity": 100,
            "cost_price": 150.0,
            "currency": "USD",
            "asset_class": "Equity",
        },
    )

    csv_data = "ticker,quantity,cost_price,currency,asset_class\nMSFT US Equity,50,320.0,USD,Equity\n"
    r = client.post(
        f"/api/portfolios/{pid}/import-csv?replace=true",
        files={"file": ("holdings.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1

    positions = client.get(f"/api/portfolios/{pid}/positions").json()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "MSFT US Equity"
