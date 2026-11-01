from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.services.historical_data_service import get_historical_candles


router = APIRouter(
    prefix="/api/historical",
    tags=["Historical Data"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/candles/{instrument_id}")
def read_historical_candles(
    instrument_id: int,
    timeframe: str = Query(..., min_length=1, max_length=10),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    db: Session = Depends(get_db),
):
    if start_time > end_time:
        raise HTTPException(
            status_code=400,
            detail="start_time must be earlier than or equal to end_time",
        )

    candles = get_historical_candles(
        db=db,
        instrument_id=instrument_id,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
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