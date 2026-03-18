# Python Event-Driven Backtesting Engine

A **custom, event-driven backtesting framework** in Python. The engine advances the clock bar-by-bar (tick-by-tick in time), routes **Market**, **Signal**, **Order**, and **Fill** events through a central queue, and updates portfolio state only when each event is processed—so strategies cannot see future prices and **look-ahead bias** is avoided. Execution simulates **commissions**, **slippage**, and supports **long and short** positions for more realistic P&amp;L.

## Architecture

Four core components communicate only via a **`queue.Queue`**:

| Component | Role |
|-----------|------|
| **DataHandler** | Streams historical bars (e.g. CSV), enqueues `MarketEvent` each step. |
| **Strategy** | Consumes market updates, emits `SignalEvent` (e.g. buy-and-hold). |
| **Portfolio** | Maps signals to orders, tracks cash/positions, applies fills, records equity. |
| **ExecutionHandler** | Turns orders into fills at the latest close (with slippage). |

The **`engine`** module wires these pieces and runs the main event loop until data is exhausted.

## Features

- **Commission simulation** — fills delegate to `FillEvent.calculate_commission`.
- **Slippage modeling** — `SimulatedExecutionHandler` widens buys and tightens sells vs. close.
- **Long / short** — portfolio handles shorts and `EXIT` to flatten.
- **Performance metrics** — annualized Sharpe (zero risk-free) and max drawdown; optional **equity + drawdown** charts via `plot.py`.

## Project layout

- `events.py` — event types  
- `data.py` — `DataHandler`, `HistoricCSVDataHandler`  
- `strategy.py` — `Strategy`, `BuyAndHoldStrategy`  
- `portfolio.py` — positions, holdings, equity curve  
- `execution.py` — `SimulatedExecutionHandler`  
- `performance.py` — Sharpe, drawdowns  
- `plot.py` — matplotlib equity / drawdown plots  
- `engine.py` — `run_backtest()`  
- `tests/` — pytest suite  

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the demo backtest (uses sample data under `data/`):

```bash
python engine.py
```

Run tests:

```bash
pytest
```

## Disclaimer

This project is for **educational and research purposes only**. It is **not** financial, investment, or trading advice. Past simulated performance does not guarantee future results. Use at your own risk.
