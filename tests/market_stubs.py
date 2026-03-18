"""
Minimal bar / data-handler stubs shared by portfolio and execution tests.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime


class _DummyBars:
    """
    Minimal data handler stub.

    Provides ``symbol_list`` and ``latest_symbol_data`` (deque per symbol)
    compatible with :class:`portfolio.Portfolio` and
    :class:`execution.SimulatedExecutionHandler`.
    """

    def __init__(self, symbol_list: list[str]) -> None:
        self.symbol_list = symbol_list
        self.latest_symbol_data = {symbol: deque(maxlen=10) for symbol in symbol_list}


class _Bar:
    """
    Lightweight stand-in for a pandas Series with a close price.
    """

    def __init__(self, timestamp: datetime, close: float) -> None:
        self.name = timestamp
        self.data = {"close": close}

    def __getitem__(self, item: str) -> float:
        return self.data[item]
