

from __future__ import annotations

from collections import deque
from datetime import datetime


class _DummyBars:
    def __init__(self, symbol_list: list[str]) -> None:
        self.symbol_list = symbol_list
        self.latest_symbol_data = {symbol: deque(maxlen=10) for symbol in symbol_list}


class _Bar:
    def __init__(self, timestamp: datetime, close: float) -> None:
        self.name = timestamp
        self.data = {"close": close}

    def __getitem__(self, item: str) -> float:
        return self.data[item]
