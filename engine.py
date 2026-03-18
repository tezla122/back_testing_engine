"""
Main event loop for the backtesting engine.

Wires the data handler, strategy, portfolio, and simulated execution
together and drains the central queue until historical data is exhausted.
"""

from __future__ import annotations

import queue
from datetime import datetime
from queue import Queue

from data import HistoricCSVDataHandler
from events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from execution import SimulatedExecutionHandler
from performance import create_drawdowns, create_sharpe_ratio
from plot import plot_performance
from portfolio import Portfolio
from strategy import BuyAndHoldStrategy


def run_backtest() -> None:
    """
    Run a minimal end-to-end backtest with dummy parameters.

    Instantiates :class:`HistoricCSVDataHandler`, :class:`BuyAndHoldStrategy`,
    :class:`Portfolio`, and :class:`SimulatedExecutionHandler`, then loops:
    advance bars, drain and route all queued events until the CSV stream
    ends. Prints routing activity and final total equity.
    """
    events_queue: Queue = Queue()

    csv_dir = "data"
    symbol_list = ["AAPL"]
    initial_capital = 100000.0
    start_date = datetime(2020, 1, 1)

    bars = HistoricCSVDataHandler(
        events_queue=events_queue,
        csv_dir=csv_dir,
        symbol_list=symbol_list,
    )
    strategy = BuyAndHoldStrategy(bars=bars, events_queue=events_queue)
    portfolio = Portfolio(
        events_queue=events_queue,
        bars=bars,
        start_date=start_date,
        initial_capital=initial_capital,
    )
    execution = SimulatedExecutionHandler(
        events_queue=events_queue,
        bars=bars,
    )

    print("Starting backtest...")
    while True:
        try:
            bars.update_bars()
        except StopIteration:
            break

        while True:
            try:
                event = events_queue.get_nowait()
            except queue.Empty:
                break

            print(f"Processing {event.type} event...")

            if event.type == "MARKET":
                if isinstance(event, MarketEvent):
                    strategy.calculate_signals(event)
                    portfolio.update_timeindex(event)
            elif event.type == "SIGNAL":
                if isinstance(event, SignalEvent):
                    portfolio.update_signal(event)
            elif event.type == "ORDER":
                if isinstance(event, OrderEvent):
                    execution.execute_order(event)
            elif event.type == "FILL":
                if isinstance(event, FillEvent):
                    portfolio.update_fill(event)
            else:
                print(f"  (unhandled event type: {event.type!r})")

    final_total = portfolio.current_holdings.get("total", 0.0)
    print(f"Backtest complete. Final portfolio equity (total): {final_total}")

    equity_df = portfolio.create_equity_curve_dataframe()
    returns = equity_df["returns"] if "returns" in equity_df.columns else None
    sharpe = (
        create_sharpe_ratio(returns, periods=252)
        if returns is not None
        else 0.0
    )
    _, max_drawdown, _ = (
        create_drawdowns(equity_df["total"])
        if "total" in equity_df.columns and not equity_df["total"].empty
        else (None, 0.0, 0.0)
    )
    print(f"Annualized Sharpe ratio (rf=0): {sharpe:.4f}")
    print(f"Maximum drawdown: {max_drawdown * 100:.2f}%")

    plot_performance(equity_df)


if __name__ == "__main__":
    run_backtest()
