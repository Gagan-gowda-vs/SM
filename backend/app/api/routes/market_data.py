from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.connection import SessionLocal
from app.schemas.market_candle import (
    MarketCandleBulkCreate,
    MarketCandleCreate,
)
from app.services.market_data_service import (
    create_candle,
    create_candles_bulk,
    get_candles,
)

router = APIRouter(
    prefix="/api/market",
    tags=["Market Data"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/candles/{instrument_id}")
def read_candles(
    instrument_id: int,
    timeframe: str = Query(..., min_length=1, max_length=10),
    limit: int = Query(100, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    candles = get_candles(
        db=db,
        instrument_id=instrument_id,
        timeframe=timeframe,
        limit=limit,
    )

    return [
        {
            "id": candle.id,
            "instrument_id": candle.instrument_id,
            "timestamp": candle.timestamp,
            "timeframe": candle.timeframe,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]


@router.post("/candles")
def add_candle(
    candle_data: MarketCandleCreate,
    db: Session = Depends(get_db),
):
    try:
        candle = create_candle(db, candle_data)

        return {
            "id": candle.id,
            "instrument_id": candle.instrument_id,
            "timestamp": candle.timestamp,
            "timeframe": candle.timeframe,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Candle already exists for this instrument, timeframe, and timestamp",
        ) from None


@router.post("/candles/bulk")
def add_candles_bulk(
    candle_data: MarketCandleBulkCreate,
    db: Session = Depends(get_db),
):
    try:
        candles = create_candles_bulk(
            db=db,
            candles_data=candle_data.candles,
        )

        return {
            "inserted": len(candles),
            "candles": [
                {
                    "id": candle.id,
                    "instrument_id": candle.instrument_id,
                    "timestamp": candle.timestamp,
                    "timeframe": candle.timeframe,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
                for candle in candles
            ],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="One or more candles already exist",
        ) from None