

from __future__ import annotations

from pathlib import Path
from queue import Queue

import pandas as pd
import pytest

#from back_testing_engine.data import HistoricCSVDataHandler
#from back_testing_engine.events import MarketEvent

from data import HistoricCSVDataHandler
from events import MarketEvent


def _create_mock_csv(tmp_path: Path, symbol: str, dates: list[str]) -> None:
    
    data = {
        "open": [1.0 * (i + 1) for i in range(len(dates))],
        "high": [1.1 * (i + 1) for i in range(len(dates))],
        "low": [0.9 * (i + 1) for i in range(len(dates))],
        "close": [1.05 * (i + 1) for i in range(len(dates))],
        "volume": [100 * (i + 1) for i in range(len(dates))],
    }
    df = pd.DataFrame(data, index=pd.to_datetime(dates))
    df.index.name = "date"
    df.to_csv(tmp_path / f"{symbol}.csv")


def test_update_bars_pulls_data_chronologically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "TEST"
    dates = ["2020-01-01", "2020-01-02", "2020-01-03"]
    _create_mock_csv(tmp_path, symbol, dates)

    events = Queue()

    handler = HistoricCSVDataHandler(events_queue=events, csv_dir=str(tmp_path), symbol_list=[symbol])

    observed_dates: list[pd.Timestamp] = []

    for _ in dates:
        handler.update_bars()
        latest_bar = handler.latest_symbol_data[symbol][-1]
        observed_dates.append(latest_bar.name)

    assert observed_dates == list(pd.to_datetime(dates))


def test_market_event_emitted_on_update(tmp_path: Path) -> None:
    symbol = "TEST"
    dates = ["2020-01-01", "2020-01-02"]
    _create_mock_csv(tmp_path, symbol, dates)

    events = Queue()
    handler = HistoricCSVDataHandler(events_queue=events, csv_dir=str(tmp_path), symbol_list=[symbol])

    handler.update_bars()

    event = events.get_nowait()
    assert isinstance(event, MarketEvent)


def test_update_bars_raises_when_data_exhausted(tmp_path: Path) -> None:
    symbol = "TEST"
    dates = ["2020-01-01"]
    _create_mock_csv(tmp_path, symbol, dates)

    events = Queue()
    handler = HistoricCSVDataHandler(events_queue=events, csv_dir=str(tmp_path), symbol_list=[symbol])

    handler.update_bars()

    with pytest.raises(StopIteration):
        handler.update_bars()

    assert handler.continue_backtest is False

