from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.historical import get_db as historical_get_db
from app.api.routes.market_data import get_db as market_get_db
from app.database.base import Base
from app.main import app
from app.models.instrument import Instrument
from app.models.market_candle import MarketCandle
from app.schemas.market_candle import MarketCandleCreate
from app.services.historical_data_service import get_historical_candles
from app.services.market_data.dhan_provider import DhanProvider
from app.services.market_data_service import create_candle, create_candles_bulk, get_candles


@pytest.fixture
def test_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    instrument = Instrument(
        symbol="NIFTY",
        name="NIFTY 50",
        instrument_type="INDEX",
    )
    session.add(instrument)
    session.commit()
    session.refresh(instrument)

    try:
        yield session, instrument
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_session):
    session, _ = test_session

    def override_market_get_db():
        yield session

    def override_historical_get_db():
        yield session

    app.dependency_overrides[market_get_db] = override_market_get_db
    app.dependency_overrides[historical_get_db] = override_historical_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_dhan_provider_can_be_created():
    provider = DhanProvider()

    assert provider is not None


def test_market_candle_schema_rejects_invalid_ohlc():
    with pytest.raises(ValidationError):
        MarketCandleCreate(
            instrument_id=1,
            timestamp=datetime.now(timezone.utc),
            timeframe="1d",
            open=100.0,
            high=90.0,
            low=95.0,
            close=110.0,
            volume=1000,
        )


def test_market_candle_schema_rejects_negative_volume():
    with pytest.raises(ValidationError):
        MarketCandleCreate(
            instrument_id=1,
            timestamp=datetime.now(timezone.utc),
            timeframe="1d",
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=-1,
        )


def test_single_candle_insertion(test_session):
    session, instrument = test_session
    candle_data = MarketCandleCreate(
        instrument_id=instrument.id,
        timestamp=datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc),
        timeframe="1d",
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=5000,
    )

    candle = create_candle(session, candle_data)

    assert candle.instrument_id == instrument.id
    assert candle.timeframe == "1d"
    assert session.query(MarketCandle).count() == 1


def test_bulk_candle_insertion(test_session):
    session, instrument = test_session
    candle_data = [
        MarketCandleCreate(
            instrument_id=instrument.id,
            timestamp=datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc),
            timeframe="1d",
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=5000,
        ),
        MarketCandleCreate(
            instrument_id=instrument.id,
            timestamp=datetime(2024, 1, 3, 9, 30, tzinfo=timezone.utc),
            timeframe="1d",
            open=105.0,
            high=115.0,
            low=100.0,
            close=110.0,
            volume=5500,
        ),
    ]

    inserted = create_candles_bulk(session, candle_data)

    assert len(inserted) == 2
    assert session.query(MarketCandle).count() == 2


def test_duplicate_candle_prevention(test_session):
    session, instrument = test_session
    candle_data = MarketCandleCreate(
        instrument_id=instrument.id,
        timestamp=datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc),
        timeframe="1d",
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=5000,
    )

    create_candle(session, candle_data)

    with pytest.raises(Exception):
        create_candle(session, candle_data)


def test_market_candle_get_endpoint(client, test_session):
    _, instrument = test_session
    payload = [
        {
            "instrument_id": instrument.id,
            "timestamp": "2024-01-02T09:30:00+00:00",
            "timeframe": "1d",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 105.0,
            "volume": 5000,
        },
        {
            "instrument_id": instrument.id,
            "timestamp": "2024-01-03T09:30:00+00:00",
            "timeframe": "1d",
            "open": 105.0,
            "high": 115.0,
            "low": 100.0,
            "close": 110.0,
            "volume": 5500,
        },
    ]

    response = client.post("/api/market/candles/bulk", json={"candles": payload})
    assert response.status_code == 200

    get_response = client.get(f"/api/market/candles/{instrument.id}?timeframe=1d&limit=10")
    assert get_response.status_code == 200
    body = get_response.json()
    assert len(body) == 2
    assert body[0]["timestamp"] == "2024-01-02T09:30:00+00:00"
    assert body[1]["timestamp"] == "2024-01-03T09:30:00+00:00"


def test_historical_candle_service_filtering_and_ordering(test_session):
    session, instrument = test_session
    timestamp_one = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)
    timestamp_two = datetime(2024, 1, 3, 9, 30, tzinfo=timezone.utc)
    timestamp_three = datetime(2024, 1, 4, 9, 30, tzinfo=timezone.utc)

    create_candles_bulk(
        session,
        [
            MarketCandleCreate(
                instrument_id=instrument.id,
                timestamp=timestamp_one,
                timeframe="1d",
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=5000,
            ),
            MarketCandleCreate(
                instrument_id=instrument.id,
                timestamp=timestamp_two,
                timeframe="1d",
                open=105.0,
                high=115.0,
                low=100.0,
                close=110.0,
                volume=5500,
            ),
            MarketCandleCreate(
                instrument_id=instrument.id,
                timestamp=timestamp_three,
                timeframe="1d",
                open=110.0,
                high=120.0,
                low=105.0,
                close=115.0,
                volume=6000,
            ),
        ],
    )

    candles = get_historical_candles(
        session,
        instrument.id,
        "1d",
        datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 3, 23, 59, tzinfo=timezone.utc),
    )

    assert [c.timestamp for c in candles] == [timestamp_one, timestamp_two]


def test_historical_candle_get_endpoint(client, test_session):
    _, instrument = test_session
    start = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 4, 23, 59, tzinfo=timezone.utc)

    for day in (2, 3, 4):
        response = client.post(
            "/api/market/candles",
            json={
                "instrument_id": instrument.id,
                "timestamp": f"2024-01-{day:02d}T09:30:00+00:00",
                "timeframe": "1d",
                "open": 100.0 + day,
                "high": 110.0 + day,
                "low": 95.0 + day,
                "close": 105.0 + day,
                "volume": 5000 + day * 100,
            },
        )
        assert response.status_code == 200

    response = client.get(
        "/api/historical/candles/{instrument_id}?timeframe=1d&start_time={start}&end_time={end}".format(
            instrument_id=instrument.id,
            start=quote(start.isoformat()),
            end=quote(end.isoformat()),
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["timestamp"] == "2024-01-02T09:30:00+00:00"
    assert body[-1]["timestamp"] == "2024-01-04T09:30:00+00:00"


def test_invalid_historical_range_returns_400(client, test_session):
    _, instrument = test_session
    start = datetime(2024, 1, 5, tzinfo=timezone.utc)
    end = datetime(2024, 1, 4, tzinfo=timezone.utc)

    response = client.get(
        "/api/historical/candles/{instrument_id}?timeframe=1d&start_time={start}&end_time={end}".format(
            instrument_id=instrument.id,
            start=quote(start.isoformat()),
            end=quote(end.isoformat()),
        )
    )

    assert response.status_code in (400, 422)


def test_market_candle_duplicate_route_returns_409(client, test_session):
    _, instrument = test_session
    payload = {
        "instrument_id": instrument.id,
        "timestamp": "2024-01-02T09:30:00+00:00",
        "timeframe": "1d",
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 105.0,
        "volume": 5000,
    }

    first = client.post("/api/market/candles", json=payload)
    second = client.post("/api/market/candles", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


def test_market_candle_route_rejects_invalid_payload(client, test_session):
    _, instrument = test_session
    payload = {
        "instrument_id": instrument.id,
        "timestamp": "2024-01-02T09:30:00+00:00",
        "timeframe": "1d",
        "open": 100.0,
        "high": 90.0,
        "low": 95.0,
        "close": 105.0,
        "volume": 5000,
    }

    response = client.post("/api/market/candles", json=payload)

    assert response.status_code == 422
