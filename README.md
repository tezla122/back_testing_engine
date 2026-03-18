# Python Event-Driven Backtesting Engine

A custom, tick-by-tick event-driven backtesting framework designed for quantitative trading research. 

Unlike vectorized backtesters that calculate returns over an entire dataset at once, this engine strictly enforces a chronological "conveyor belt" of data. By processing the market bar-by-bar through a central event queue, it completely eliminates look-ahead bias and allows for a highly realistic simulation of market mechanics, making it easy to transition from backtesting to live paper trading.

## ✨ Key Features

* **Strict Look-Ahead Bias Prevention:** Data is yielded strictly chronological via an iterator design.
* **Realistic Market Friction:** Built-in simulated execution handling including percentage-based slippage and transaction commissions.
* **Comprehensive Portfolio Accounting:** Mark-to-market daily revaluation, cash management, and support for both Long and Short positions.
* **Performance Analytics:** Automated calculation of annualized Sharpe Ratios and Maximum Drawdown.
* **Visualization Suite:** Generates professional-grade matplotlib charts displaying the equity curve alongside an "underwater" drawdown plot.

## 🏗️ Architecture

The engine is built around a central Python `queue.Queue()` and relies on four primary components communicating via standardized Event objects:

1. **DataHandler (`data.py`):** Ingests historical CSV data and yields `MarketEvents` bar-by-bar.
2. **Strategy (`strategy.py`):** Subscribes to market data, calculates trading logic, and generates `SignalEvents` (LONG/SHORT/EXIT).
3. **Portfolio (`portfolio.py`):** Acts as the risk manager and accountant. It translates signals into `OrderEvents` based on available capital and tracks the total net worth of the account.
4. **ExecutionHandler (`execution.py`):** Simulates a brokerage fill. It catches orders, applies slippage, calculates costs, and returns `FillEvents`.

## 📂 Project Structure

```text
back_testing_engine/
├── data/                   # Directory for historical CSV data (e.g., AAPL.csv)
├── tests/                  # Pytest unit testing suite
├── engine.py               # The main event loop and backtest entry point
├── events.py               # Definitions for Market, Signal, Order, and Fill events
├── data.py                 # Historical CSV data ingestion
├── portfolio.py            # Position tracking and cash management
├── execution.py            # Simulated broker execution and slippage
├── strategy.py             # Trading strategy interfaces (e.g., BuyAndHold)
├── performance.py          # Math module for Sharpe Ratio and Drawdowns
├── plot.py                 # Matplotlib visualization logic
└── requirements.txt        # Python dependencies
