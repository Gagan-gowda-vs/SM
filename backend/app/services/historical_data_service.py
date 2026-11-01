from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_candle import MarketCandle


def _normalize_timestamp(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_historical_candles(
    db: Session,
    instrument_id: int,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
):
    candles = db.scalars(
        select(MarketCandle)
        .where(
            MarketCandle.instrument_id == instrument_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.timestamp >= start_time,
            MarketCandle.timestamp <= end_time,
        )
        .order_by(MarketCandle.timestamp.asc())
    ).all()

    normalized = []
    for candle in candles:
        candle.timestamp = _normalize_timestamp(candle.timestamp)
        normalized.append(candle)

    return list(normalized)