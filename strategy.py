
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from queue import Queue

from data import DataHandler
from events import MarketEvent, SignalEvent


class Strategy(metaclass=ABCMeta):
   

    @abstractmethod
    def calculate_signals(self, event: object) -> None:



class BuyAndHoldStrategy(Strategy):
   

    def __init__(self, bars: DataHandler, events_queue: Queue) -> None:
        self.bars: DataHandler = bars
        self.events_queue: Queue = events_queue
        self.bought: dict[str, bool] = {
            symbol: False for symbol in bars.symbol_list
        }

    def calculate_signals(self, event: MarketEvent) -> None:
      
        if not isinstance(event, MarketEvent) or event.type != "MARKET":
            return

        for symbol in self.bars.symbol_list:
            if self.bought[symbol]:
                continue
            latest = self.bars.latest_symbol_data.get(symbol)
            if not latest:
                continue
            bar = latest[-1]
            bar_dt = bar.name
            signal = SignalEvent(
                strategy_id="BuyAndHold",
                symbol=symbol,
                datetime=bar_dt,
                signal_type="LONG",
                strength=1.0,
            )
            self.events_queue.put(signal)
            self.bought[symbol] = True
