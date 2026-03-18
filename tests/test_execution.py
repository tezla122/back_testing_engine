"""
Unit tests for SimulatedExecutionHandler.
"""

from __future__ import annotations

from datetime import datetime
from queue import Queue

import pytest

from events import FillEvent, OrderEvent
from execution import SimulatedExecutionHandler

from market_stubs import _Bar, _DummyBars


def test_execute_order_enqueues_fill_at_latest_close() -> None:
    """
    A market BUY order should produce one FillEvent at slippage-adjusted price.
    Default slippage is 5 bps: 150 * 1.0005 * 100.
    """
    bar_time = datetime(2020, 6, 15, 16, 0, 0)
    bars = _DummyBars(symbol_list=["AAPL"])
    bars.latest_symbol_data["AAPL"].append(_Bar(timestamp=bar_time, close=150.0))

    events: Queue[FillEvent] = Queue()
    handler = SimulatedExecutionHandler(events_queue=events, bars=bars)

    order = OrderEvent(
        symbol="AAPL",
        order_type="MKT",
        quantity=100,
        direction="BUY",
    )
    handler.execute_order(order)

    assert events.qsize() == 1
    fill = events.get_nowait()
    assert isinstance(fill, FillEvent)
    assert fill.symbol == "AAPL"
    assert fill.direction == "BUY"
    assert fill.quantity == 100
    expected = 150.0 * (1.0 + 0.0005) * 100.0
    assert fill.fill_cost == pytest.approx(expected)
    assert fill.exchange == "ARCA"
    assert fill.commission is None


def test_execution_applies_slippage() -> None:
    """
    BUY pays above mid; SELL receives below mid when slippage_pct is set.
    """
    bar_time = datetime(2020, 6, 15, 16, 0, 0)
    bars = _DummyBars(symbol_list=["AAPL"])
    bars.latest_symbol_data["AAPL"].append(_Bar(timestamp=bar_time, close=100.0))
    events: Queue[FillEvent] = Queue()
    slip = 0.01
    handler = SimulatedExecutionHandler(
        events_queue=events, bars=bars, slippage_pct=slip
    )

    buy = OrderEvent(
        symbol="AAPL",
        order_type="MKT",
        quantity=50,
        direction="BUY",
    )
    handler.execute_order(buy)
    fill_buy = events.get_nowait()
    assert fill_buy.fill_cost == pytest.approx(101.0 * 50.0)

    sell = OrderEvent(
        symbol="AAPL",
        order_type="MKT",
        quantity=25,
        direction="SELL",
    )
    handler.execute_order(sell)
    fill_sell = events.get_nowait()
    assert fill_sell.fill_cost == pytest.approx(99.0 * 25.0)
