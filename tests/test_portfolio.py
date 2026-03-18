

from __future__ import annotations

from datetime import datetime
from queue import Queue

import pytest

from events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from portfolio import Portfolio

from market_stubs import _Bar, _DummyBars


def test_portfolio_initialisation_sets_cash_and_total() -> None:
   

    start_date = datetime(2020, 1, 1)
    events = Queue()
    bars = _DummyBars(symbol_list=["AAPL"])

    initial_capital = 50_000.0
    portfolio = Portfolio(
        events_queue=events,
        bars=bars,
        start_date=start_date,
        initial_capital=initial_capital,
    )

    assert portfolio.current_holdings["cash"] == pytest.approx(initial_capital)
    assert portfolio.current_holdings["total"] == pytest.approx(initial_capital)
    assert portfolio.current_holdings["commission"] == pytest.approx(0.0)


def test_update_signal_enqueues_long_order() -> None:
  

    start_date = datetime(2020, 1, 1)
    events: Queue[OrderEvent] = Queue()
    bars = _DummyBars(symbol_list=["AAPL"])

    portfolio = Portfolio(
        events_queue=events,
        bars=bars,
        start_date=start_date,
    )

    signal = SignalEvent(
        strategy_id="test_strategy",
        symbol="AAPL",
        datetime=start_date,
        signal_type="LONG",
    )

    portfolio.update_signal(signal)

    order = events.get_nowait()
    assert isinstance(order, OrderEvent)
    assert order.symbol == "AAPL"
    assert order.order_type == "MKT"
    assert order.direction == "BUY"
    assert order.quantity == 100


def test_update_fill_updates_positions_and_cash() -> None:
  

    start_date = datetime(2020, 1, 1)
    events = Queue()
    bars = _DummyBars(symbol_list=["AAPL"])

    initial_capital = 20_000.0
    portfolio = Portfolio(
        events_queue=events,
        bars=bars,
        start_date=start_date,
        initial_capital=initial_capital,
    )

    fill = FillEvent(
        timeindex=start_date,
        symbol="AAPL",
        exchange="TEST_EXCHANGE",
        quantity=100,
        direction="BUY",
        fill_cost=150.0 * 100,
        commission=1.0,
    )

    starting_cash = portfolio.current_holdings["cash"]
    portfolio.update_fill(fill)
    ending_cash = portfolio.current_holdings["cash"]

    assert portfolio.current_positions["AAPL"] == 100
    assert pytest.approx(starting_cash - ending_cash) == 15_001.0


def test_update_timeindex_revalues_positions() -> None:
 
    start_date = datetime(2020, 1, 1)
    events = Queue()
    bars = _DummyBars(symbol_list=["AAPL"])

    portfolio = Portfolio(
        events_queue=events,
        bars=bars,
        start_date=start_date,
        initial_capital=10_000.0,
    )

    portfolio.current_positions["AAPL"] = 10
    bar_time = datetime(2020, 1, 2)
    bars.latest_symbol_data["AAPL"].append(_Bar(timestamp=bar_time, close=100.0))

    market_event = MarketEvent()
    portfolio.update_timeindex(market_event)

    assert portfolio.current_holdings["AAPL"] == pytest.approx(1_000.0)
    assert portfolio.current_holdings["total"] == pytest.approx(11_000.0)


def test_portfolio_handles_short_and_exit() -> None:
   
    start_date = datetime(2020, 1, 1)
    events: Queue[OrderEvent] = Queue()
    bars = _DummyBars(symbol_list=["AAPL"])
    portfolio = Portfolio(
        events_queue=events,
        bars=bars,
        start_date=start_date,
    )

    short_sig = SignalEvent(
        strategy_id="test",
        symbol="AAPL",
        datetime=start_date,
        signal_type="SHORT",
    )
    portfolio.update_signal(short_sig)
    o1 = events.get_nowait()
    assert o1.direction == "SELL"
    assert o1.quantity == 100

    portfolio.current_positions["AAPL"] = -100
    exit_sig = SignalEvent(
        strategy_id="test",
        symbol="AAPL",
        datetime=start_date,
        signal_type="EXIT",
    )
    portfolio.update_signal(exit_sig)
    o2 = events.get_nowait()
    assert o2.direction == "BUY"
    assert o2.quantity == 100

