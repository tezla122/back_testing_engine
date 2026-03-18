"""
Data handling abstractions for the backtesting engine.

This module provides the :class:`DataHandler` abstract base class and a
simple CSV-backed historical implementation suitable for event-driven
backtests that strictly avoid look-ahead bias.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Generator, Iterable, List, Optional

from queue import Queue

import pandas as pd

from events import MarketEvent


class DataHandler(metaclass=ABCMeta):
    """
    Abstract base class for all data handlers.

    Concrete implementations are responsible for providing a stream of
    market data bars to the backtesting engine and for signaling the
    arrival of new data via :class:`~events.MarketEvent` instances.
    """

    @abstractmethod
    def update_bars(self) -> None:
        """
        Advance the data handler to the next bar.

        Implementations must:

        - Update any internal state that stores the *latest* bar(s).
        - Place a :class:`MarketEvent` instance onto the central
          event queue to signal that new data is available.

        The method must *not* expose future data, thereby preventing
        look-ahead bias. Only the current bar and any historical bars
        encountered up to this point may be accessible.
        """


@dataclass
class HistoricCSVDataHandler(DataHandler):
    """
    Historic data handler that reads bar data from CSV files.

    Parameters
    ----------
    events_queue:
        The central event queue used by the backtesting engine.
    csv_dir:
        Directory containing one CSV file per symbol.
    symbol_list:
        List of symbol tickers corresponding to CSV filenames
        (e.g. a symbol ``'AAPL'`` expects ``AAPL.csv`` in ``csv_dir``).

    Notes
    -----
    - Each CSV file must contain a date or datetime index column that
      can be parsed by :func:`pandas.read_csv` with ``parse_dates``.
    - Data is converted to a per-symbol generator that yields one row
      at a time. The handler steps all symbols forward in lockstep
      according to their chronological order.
    - The design ensures that at any time only the current and
      historical bars are accessible; future rows are never loaded
      into the latest-bar store before their corresponding
      :meth:`update_bars` call.
    """

    events_queue: Queue
    csv_dir: str
    symbol_list: List[str]

    continue_backtest: bool = True

    def __post_init__(self) -> None:
        self._csv_path = Path(self.csv_dir)
        self._symbol_data: Dict[str, Generator[pd.Series, None, None]] = {}
        self.latest_symbol_data: Dict[str, Deque[pd.Series]] = {
            symbol: deque(maxlen=1000) for symbol in self.symbol_list
        }

        self._load_csv_files()

    def _load_csv_files(self) -> None:
       

        for symbol in self.symbol_list:
            file_path = self._csv_path / f"{symbol}.csv"
            if not file_path.exists():
                raise FileNotFoundError(f"CSV file for symbol '{symbol}' not found at {file_path}")

            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            df.sort_index(inplace=True)

            self._symbol_data[symbol] = self._row_generator(df)
    #decorator -> tells python this func doesn't need to look at self to do its job 
    @staticmethod
    def _row_generator(df: pd.DataFrame) -> Generator[pd.Series, None, None]:
       

        for _, row in df.iterrows():
            yield row

    def _get_next_bar(self, symbol: str) -> Optional[pd.Series]:
       

        gen = self._symbol_data.get(symbol)
        if gen is None:
            raise KeyError(f"No data generator found for symbol '{symbol}'")

        try:
            return next(gen)
        except StopIteration:
            return None

    def update_bars(self) -> None:
       

        if not self.continue_backtest:
            raise StopIteration("No further data available for backtest.")

        for symbol in self.symbol_list:
            bar = self._get_next_bar(symbol)
            if bar is None:
                self.continue_backtest = False
                raise StopIteration(f"No more data for symbol '{symbol}'.")
            self.latest_symbol_data[symbol].append(bar)

        self.events_queue.put(MarketEvent())

