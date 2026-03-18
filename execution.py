

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from queue import Queue

from data import DataHandler
from events import FillEvent, OrderEvent


class ExecutionHandler(metaclass=ABCMeta):
 

    @abstractmethod
    def execute_order(self, event: OrderEvent) -> None:
       


class SimulatedExecutionHandler(ExecutionHandler):
   
    def __init__(
        self,
        events_queue: Queue,
        bars: DataHandler,
        slippage_pct: float = 0.0005,
    ) -> None:
        self.events_queue: Queue = events_queue
        self.bars: DataHandler = bars
        self.slippage_pct: float = float(slippage_pct)

    def execute_order(self, event: OrderEvent) -> None:
       
        if event.type != "ORDER":
            raise ValueError("execute_order expects an OrderEvent.")

        symbol = event.symbol
        latest = self.bars.latest_symbol_data.get(symbol)
        if not latest:
            raise ValueError(
                f"No latest bar data for symbol '{symbol}'; cannot simulate fill."
            )

        bar = latest[-1]
        timestamp = bar.name
        latest_price = float(bar["close"])
        if event.direction == "BUY":
            effective_price = latest_price * (1.0 + self.slippage_pct)
        else:
            effective_price = latest_price * (1.0 - self.slippage_pct)
        fill_cost = effective_price * float(event.quantity)

        fill = FillEvent(
            timeindex=timestamp,
            symbol=symbol,
            exchange="ARCA",
            quantity=event.quantity,
            direction=event.direction,
            fill_cost=fill_cost,
            commission=None,
        )
        self.events_queue.put(fill)
