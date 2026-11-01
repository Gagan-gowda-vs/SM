from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class MarketCandleCreate(BaseModel):
    instrument_id: int
    timestamp: datetime
    timeframe: str = Field(min_length=1, max_length=10)

    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.high < self.open:
            raise ValueError("High cannot be lower than open")

        if self.high < self.close:
            raise ValueError("High cannot be lower than close")

        if self.high < self.low:
            raise ValueError("High cannot be lower than low")

        if self.low > self.open:
            raise ValueError("Low cannot be higher than open")

        if self.low > self.close:
            raise ValueError("Low cannot be higher than close")

        return self


class MarketCandleBulkCreate(BaseModel):
    candles: list[MarketCandleCreate]