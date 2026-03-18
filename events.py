

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


class Event:
 

    type: str


@dataclass(slots=True)
class MarketEvent(Event):


    type: str = field(init=False, default="MARKET")


SignalType = Literal["LONG", "SHORT", "EXIT"]


@dataclass(slots=True)
class SignalEvent(Event):
    strategy_id: str
    symbol: str
    datetime: datetime
    signal_type: SignalType
    strength: float = 1.0

    type: str = field(init=False, default="SIGNAL")


OrderType = Literal["MKT", "LMT"]
OrderDirection = Literal["BUY", "SELL"]


@dataclass(slots=True)
class OrderEvent(Event):

    symbol: str
    order_type: OrderType
    quantity: int
    direction: OrderDirection

    type: str = field(init=False, default="ORDER")

    def print_order(self) -> None:
       

        print(
            f"Order: Symbol={self.symbol}, "
            f"Type={self.order_type}, "
            f"Quantity={self.quantity}, "
            f"Direction={self.direction}"
        )


FillDirection = OrderDirection


@dataclass(slots=True)
class FillEvent(Event):
    

    timeindex: datetime
    symbol: str
    exchange: str
    quantity: int
    direction: FillDirection
    fill_cost: float
    commission: Optional[float] = None

    type: str = field(init=False, default="FILL")

    def calculate_commission(
        self, minimum: float = 1.0, rate: float = 0.0005
    ) -> float:
       

        if self.commission is None:
            trade_value = abs(self.fill_cost)
            self.commission = max(minimum, rate * trade_value)
        return self.commission

