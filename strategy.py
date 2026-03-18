"""
Strategy interface and reference implementations.

Strategies consume market events and emit trading signals onto the
central event queue for the portfolio to interpret.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from queue import Queue

from data import DataHandler
from events import MarketEvent, SignalEvent


class Strategy(metaclass=ABCMeta):
    """
    Abstract base class for trading strategies.

    Subclasses implement :meth:`calculate_signals` to react to incoming
    events (typically :class:`~events.MarketEvent`) and enqueue
    :class:`~events.SignalEvent` instances as needed.
    """

    @abstractmethod
    def calculate_signals(self, event: object) -> None:
        """
        Evaluate the strategy and optionally emit signals.

        Parameters
        ----------
        event:
            The event that triggered evaluation (e.g. a market update).
        """


class BuyAndHoldStrategy(Strategy):
    """
    Emits a single LONG signal per symbol on the first bar, then holds.

    On each :class:`~events.MarketEvent`, every symbol that has not yet
    been marked as purchased receives one ``LONG`` signal at the latest
    bar timestamp; thereafter ``bought[symbol]`` prevents repeat entries.

    Parameters
    ----------
    bars:
        Data handler providing ``symbol_list`` and ``latest_symbol_data``.
    events_queue:
        Queue onto which :class:`~events.SignalEvent` instances are placed.
    """

    def __init__(self, bars: DataHandler, events_queue: Queue) -> None:
        self.bars: DataHandler = bars
        self.events_queue: Queue = events_queue
        self.bought: dict[str, bool] = {
            symbol: False for symbol in bars.symbol_list
        }

    def calculate_signals(self, event: MarketEvent) -> None:
        """
        On a market update, issue at most one LONG per symbol (first bar only).

        Parameters
        ----------
        event:
            The :class:`~events.MarketEvent` signalling new bar data.
        """
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
