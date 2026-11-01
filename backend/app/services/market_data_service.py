from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.models.market_candle import MarketCandle
from app.schemas.market_candle import MarketCandleCreate


def _normalize_timestamp(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _assign_candle_id(db: Session, candle: MarketCandle, next_id: int | None = None) -> int | None:
    if candle.id is not None:
        return candle.id

    if next_id is None:
        max_id = db.execute(
            select(MarketCandle.id).order_by(MarketCandle.id.desc()).limit(1)
        ).scalar()
        next_id = (max_id or 0) + 1

    candle.id = next_id
    return next_id + 1


def create_candle(
    db: Session,
    candle_data: MarketCandleCreate,
) -> MarketCandle:

    instrument = db.scalar(
        select(Instrument).where(
            Instrument.id == candle_data.instrument_id
        )
    )

    if instrument is None:
        raise ValueError("Instrument not found")

    candle = MarketCandle(
        instrument_id=candle_data.instrument_id,
        timestamp=candle_data.timestamp,
        timeframe=candle_data.timeframe,
        open=candle_data.open,
        high=candle_data.high,
        low=candle_data.low,
        close=candle_data.close,
        volume=candle_data.volume,
    )
    _assign_candle_id(db, candle)

    db.add(candle)
    db.commit()
    db.refresh(candle)

    return candle


def get_candles(
    db: Session,
    instrument_id: int,
    timeframe: str,
    limit: int = 100,
):
    candles = db.scalars(
        select(MarketCandle)
        .where(
            MarketCandle.instrument_id == instrument_id,
            MarketCandle.timeframe == timeframe,
        )
        .order_by(MarketCandle.timestamp.desc())
        .limit(limit)
    ).all()

    normalized = []
    for candle in candles:
        candle.timestamp = _normalize_timestamp(candle.timestamp)
        normalized.append(candle)

    return list(reversed(normalized))


def create_candles_bulk(
    db: Session,
    candles_data: list[MarketCandleCreate],
):
    instruments = {
        instrument.id
        for instrument in db.scalars(
            select(Instrument)
        ).all()
    }

    for candle_data in candles_data:
        if candle_data.instrument_id not in instruments:
            raise ValueError(
                f"Instrument {candle_data.instrument_id} not found"
            )

    candles = []
    next_id = (db.execute(
        select(MarketCandle.id).order_by(MarketCandle.id.desc()).limit(1)
    ).scalar() or 0) + 1

    for candle_data in candles_data:
        candle = MarketCandle(
            instrument_id=candle_data.instrument_id,
            timestamp=candle_data.timestamp,
            timeframe=candle_data.timeframe,
            open=candle_data.open,
            high=candle_data.high,
            low=candle_data.low,
            close=candle_data.close,
            volume=candle_data.volume,
        )
        next_id = _assign_candle_id(db, candle, next_id)
        candles.append(candle)

    try:
        db.add_all(candles)
        db.commit()

        for candle in candles:
            db.refresh(candle)

        return candles

    except Exception:
        db.rollback()
        raise