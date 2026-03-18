

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
    

    @abstractmethod
    def update_bars(self) -> None:
       

@dataclass
class HistoricCSVDataHandler(DataHandler):


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

