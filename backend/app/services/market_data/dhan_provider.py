from app.services.market_data.provider import MarketDataProvider


class DhanProvider(MarketDataProvider):

    def get_historical_candles(
        self,
        instrument_id: int,
        timeframe: str,
        start_time,
        end_time,
    ):
        raise NotImplementedError(
            "Dhan historical candle integration is not connected yet."
        )

    def get_live_quotes(
        self,
        instrument_ids: list[int],
    ):
        raise NotImplementedError(
            "Dhan live quote integration is not connected yet."
        )

    def get_option_chain(
        self,
        instrument_id: int,
    ):
        raise NotImplementedError(
            "Dhan option chain integration is not connected yet."
        )

    def get_market_depth(
        self,
        instrument_ids: list[int],
    ):
        raise NotImplementedError(
            "Dhan market depth integration is not connected yet."
        )