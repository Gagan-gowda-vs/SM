from abc import ABC, abstractmethod


class MarketDataProvider(ABC):

    @abstractmethod
    def get_historical_candles(
        self,
        instrument_id: int,
        timeframe: str,
        start_time,
        end_time,
    ):
        pass

    @abstractmethod
    def get_live_quotes(
        self,
        instrument_ids: list[int],
    ):
        pass

    @abstractmethod
    def get_option_chain(
        self,
        instrument_id: int,
    ):
        pass

    @abstractmethod
    def get_market_depth(
        self,
        instrument_ids: list[int],
    ):
        pass