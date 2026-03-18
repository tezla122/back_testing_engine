"""
Simulated order execution for the event-driven backtesting engine.

This module defines the :class:`ExecutionHandler` abstract interface and a
simple :class:`SimulatedExecutionHandler` that fills market orders at
the latest available bar close and enqueues :class:`~events.FillEvent`
instances for downstream components (e.g. portfolio).
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from queue import Queue

from data import DataHandler
from events import FillEvent, OrderEvent


class ExecutionHandler(metaclass=ABCMeta):
    """
    Abstract base class for execution / brokerage simulation.

    Concrete handlers consume :class:`~events.OrderEvent` instances and
    produce :class:`~events.FillEvent` instances (typically by placing
    them on the central event queue).
    """

    @abstractmethod
    def execute_order(self, event: OrderEvent) -> None:
        """
        Process an order and emit fills as appropriate.

        Parameters
        ----------
        event:
            The order to execute.
        """


class SimulatedExecutionHandler(ExecutionHandler):
    """
    Fills orders at the latest bar close with optional proportional slippage.

    Parameters
    ----------
    events_queue:
        Central event queue; completed fills are pushed here.
    bars:
        Data handler providing ``latest_symbol_data``: a mapping from
        symbol to a deque of bar objects. Each bar must expose a
        ``'close'`` price and a timestamp via the ``name`` attribute
        (e.g. pandas ``Series``).
    slippage_pct:
        One-sided slippage as a fraction of price (default ``0.0005``, i.e.
        5 bps). Buys fill worse (higher); sells fill worse (lower).

    Notes
    -----
    - Effective fill price: ``close * (1 + slippage_pct)`` for ``BUY``,
      ``close * (1 - slippage_pct)`` for ``SELL``.
    - Exchange is fixed to ``'ARCA'`` for simulation.
    - ``commission`` on the fill is left as ``None`` so
      :meth:`FillEvent.calculate_commission` can apply its default model
      when the portfolio or other consumer resolves it.
    """

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
        """
        Simulate an immediate fill at the slippage-adjusted price.

        Raises
        ------
        ValueError
            If ``event`` is not an order, or no bar data exists for the symbol.
        """
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
