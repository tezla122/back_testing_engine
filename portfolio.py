"""
Portfolio management for the event-driven backtesting engine.

This module defines the :class:`Portfolio` class, which is responsible
for tracking positions, cash, and overall equity through time as market
data, trading signals, and order fills are processed.
"""

from __future__ import annotations

import logging
import math
from copy import deepcopy
from datetime import datetime
from typing import Dict, List

import pandas as pd
from queue import Queue

from data import DataHandler
from events import FillEvent, MarketEvent, OrderEvent, SignalEvent

logger = logging.getLogger(__name__)


class Portfolio:
    """
    Tracks positions, cash, and equity for a backtest.

    The portfolio maintains both *current* state and a full historical
    record of positions and holdings that can be inspected or exported
    after the backtest completes.

    Parameters
    ----------
    events_queue:
        The central event queue used by the backtesting engine.
    bars:
        Reference to the data handler that provides latest bar data.
        The handler is expected to expose a ``symbol_list`` attribute
        and a ``latest_symbol_data`` mapping of symbol to a deque of
        pandas ``Series`` objects, where each series has a ``'close'``
        field and its index label is the bar timestamp.
    start_date:
        The datetime at which the portfolio is initialised.
    initial_capital:
        Starting cash balance for the portfolio. Defaults to 100,000.0.
    """

    def __init__(
        self,
        events_queue: Queue,
        bars: DataHandler,
        start_date: datetime,
        initial_capital: float = 100000.0,
    ) -> None:
        self.events_queue: Queue = events_queue
        self.bars: DataHandler = bars
        self.start_date: datetime = start_date
        self.initial_capital: float = float(initial_capital)

        self.symbol_list: List[str] = list(getattr(self.bars, "symbol_list", []))

        # Position tracking: integer quantities per symbol.
        self.all_positions: List[Dict[str, int]] = []
        self.current_positions: Dict[str, int] = {}

        # Holdings tracking: cash, commission, per-symbol market value,
        # and total equity.
        self.all_holdings: List[Dict[str, float]] = []
        self.current_holdings: Dict[str, float] = {}

        self._initialise_positions()
        self._initialise_holdings()

    # ------------------------------------------------------------------
    # Internal initialisation helpers
    # ------------------------------------------------------------------
    def _initialise_positions(self) -> None:
        """
        Create the initial positions dictionaries.

        All symbol positions start at zero. A snapshot with the start
        date is stored in :attr:`all_positions`.
        """

        self.current_positions = {symbol: 0 for symbol in self.symbol_list}
        initial_snapshot: Dict[str, int] = {"datetime": self.start_date}
        initial_snapshot.update(self.current_positions)
        self.all_positions.append(initial_snapshot)

    def _initialise_holdings(self) -> None:
        """
        Create the initial holdings dictionaries.

        All symbol market values start at zero, cash is set to the
        initial capital, commission is zero, and total equity equals
        the cash balance.
        """

        self.current_holdings = {
            "cash": self.initial_capital,
            "commission": 0.0,
            "total": self.initial_capital,
        }
        for symbol in self.symbol_list:
            self.current_holdings[symbol] = 0.0

        initial_snapshot: Dict[str, float] = {"datetime": self.start_date}
        initial_snapshot.update(self.current_holdings)
        self.all_holdings.append(initial_snapshot)

    def create_equity_curve_dataframe(self) -> pd.DataFrame:
        """
        Build a time-ordered equity curve with per-period returns.

        Flattens :attr:`all_holdings` into a :class:`~pandas.DataFrame`,
        parses ``datetime``, sorts chronologically, and sets the index
        to ``datetime``. The ``returns`` column is the percentage change
        of the ``total`` equity column (first row is NaN).

        Returns
        -------
        pd.DataFrame
            Index: ``datetime``. Includes at least ``total`` and
            ``returns``; other holding columns are preserved when present.
        """
        if not self.all_holdings:
            return pd.DataFrame(columns=["total", "returns"])

        df = pd.DataFrame(self.all_holdings)
        if "datetime" not in df.columns or "total" not in df.columns:
            out = pd.DataFrame(columns=["total", "returns"])
            return out

        df = df.copy()
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"])
        df = df.sort_values("datetime").drop_duplicates(
            subset=["datetime"], keep="last"
        )
        df = df.set_index("datetime")
        df["returns"] = df["total"].pct_change()
        return df

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def update_timeindex(self, event: MarketEvent) -> None:
        """
        Update portfolio state at a new market timestamp.

        This should be called in response to a :class:`MarketEvent`.
        The method:

        - Retrieves the latest close price for each symbol.
        - Revalues open positions using latest closes when data is valid.
        - Symbols with missing bars, invalid ``close``, non-finite price,
          negative price, or **zero** close are skipped for that bar: the
          last marked market value for that symbol is reused (or 0 if
          none), and a warning is logged.
        - Recomputes total equity as cash plus position market values.
        - Appends snapshots to :attr:`all_positions` and
          :attr:`all_holdings`.

        Parameters
        ----------
        event:
            The triggering market event. Its payload is not used, but
            the parameter is kept for interface consistency.
        """

        if event.type != "MARKET":
            raise ValueError("update_timeindex expects a MarketEvent.")

        latest_timestamp: datetime | None = None

        # Determine the current timestamp from any symbol that has data.
        for symbol in self.symbol_list:
            bars = self.bars.latest_symbol_data.get(symbol)
            if bars:
                latest_bar = bars[-1]
                latest_timestamp = latest_bar.name
                break

        if latest_timestamp is None:
            # No market data yet; nothing to update.
            return

        # Update positions snapshot.
        pos_snapshot: Dict[str, int] = {"datetime": latest_timestamp}
        pos_snapshot.update(self.current_positions)
        self.all_positions.append(deepcopy(pos_snapshot))

        # Revalue holdings based on latest close prices.
        holdings_snapshot: Dict[str, float] = {
            "datetime": latest_timestamp,
            "cash": self.current_holdings["cash"],
            "commission": self.current_holdings["commission"],
        }

        total_equity = self.current_holdings["cash"]

        for symbol in self.symbol_list:
            position_qty = self.current_positions.get(symbol, 0)
            bars = self.bars.latest_symbol_data.get(symbol)
            prior_mark = float(self.current_holdings.get(symbol, 0.0))

            if not bars:
                logger.warning(
                    "No bar data for %s; skipping revaluation, using last mark %.2f.",
                    symbol,
                    prior_mark,
                )
                market_value = prior_mark
            else:
                latest_bar = bars[-1]
                try:
                    raw_close = latest_bar["close"]
                except (KeyError, TypeError):
                    logger.warning(
                        "Missing or invalid close for %s; skipping revaluation.",
                        symbol,
                    )
                    market_value = prior_mark
                else:
                    try:
                        price = float(raw_close)
                    except (TypeError, ValueError):
                        logger.warning(
                            "Non-numeric close for %s; skipping revaluation.",
                            symbol,
                        )
                        market_value = prior_mark
                    else:
                        if not math.isfinite(price):
                            logger.warning(
                                "Non-finite close for %s; skipping revaluation.",
                                symbol,
                            )
                            market_value = prior_mark
                        elif price < 0:
                            logger.warning(
                                "Negative close for %s; skipping revaluation.",
                                symbol,
                            )
                            market_value = prior_mark
                        elif price == 0.0:
                            logger.warning(
                                "Close is zero for %s; skipping revaluation "
                                "(using last mark).",
                                symbol,
                            )
                            market_value = prior_mark
                        else:
                            market_value = position_qty * price

            self.current_holdings[symbol] = market_value
            holdings_snapshot[symbol] = market_value
            total_equity += market_value

        self.current_holdings["total"] = total_equity
        holdings_snapshot["total"] = total_equity

        self.all_holdings.append(deepcopy(holdings_snapshot))

    def update_signal(self, event: SignalEvent) -> None:
        """
        React to a trading signal by generating an order.

        Naive sizing rules:

        - ``LONG``: market **BUY** 100 shares.
        - ``SHORT``: market **SELL** 100 shares (open or add to short).
        - ``EXIT``: close flat for that symbol only — if long (> 0),
          **SELL** the full quantity; if short (< 0), **BUY** to cover
          (quantity ``abs(position)``); if flat (0), no order.

        The generated :class:`OrderEvent` is placed onto the
        :attr:`events_queue`.

        Parameters
        ----------
        event:
            The :class:`SignalEvent` emitted by a strategy.
        """

        if event.type != "SIGNAL":
            raise ValueError("update_signal expects a SignalEvent.")

        symbol = event.symbol
        signal_type = event.signal_type

        order: OrderEvent | None = None

        if signal_type == "LONG":
            order = OrderEvent(
                symbol=symbol,
                order_type="MKT",
                quantity=100,
                direction="BUY",
            )
        elif signal_type == "SHORT":
            order = OrderEvent(
                symbol=symbol,
                order_type="MKT",
                quantity=100,
                direction="SELL",
            )
        elif signal_type == "EXIT":
            current_qty = self.current_positions.get(symbol, 0)
            if current_qty > 0:
                order = OrderEvent(
                    symbol=symbol,
                    order_type="MKT",
                    quantity=int(current_qty),
                    direction="SELL",
                )
            elif current_qty < 0:
                order = OrderEvent(
                    symbol=symbol,
                    order_type="MKT",
                    quantity=int(abs(current_qty)),
                    direction="BUY",
                )

        if order is not None:
            self.events_queue.put(order)

    def update_fill(self, event: FillEvent) -> None:
        """
        Update portfolio positions and cash based on a fill.

        This method applies the effects of a :class:`FillEvent` by:

        - Adjusting the position quantity for the filled symbol.
        - Deducting or crediting cash for the fill cost.
        - Deducting explicit commissions from cash and accumulating them
          in the ``commission`` field.

        Short positions are permitted and are represented by negative
        quantities in :attr:`current_positions`.

        Parameters
        ----------
        event:
            The :class:`FillEvent` describing the executed trade.
        """

        if event.type != "FILL":
            raise ValueError("update_fill expects a FillEvent.")

        symbol = event.symbol
        direction_multiplier = 1 if event.direction == "BUY" else -1

        # Update position quantity; negative values represent shorts.
        prev_qty = self.current_positions.get(symbol, 0)
        self.current_positions[symbol] = prev_qty + direction_multiplier * event.quantity

        # Determine commission using the event's commission model.
        commission = event.calculate_commission()
        self.current_holdings["commission"] += commission

        # Update cash: BUY reduces cash, SELL increases it. Commission
        # always reduces cash.
        cash_change = -(direction_multiplier * event.fill_cost + commission)
        self.current_holdings["cash"] += cash_change

