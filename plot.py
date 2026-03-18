
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from performance import create_drawdowns


def plot_performance(equity_curve_df: pd.DataFrame) -> None:
   
    if equity_curve_df is None or equity_curve_df.empty:
        return
    if "total" not in equity_curve_df.columns:
        return

    total = pd.to_numeric(equity_curve_df["total"], errors="coerce").dropna()
    if total.empty:
        return

    drawdown, _, _ = create_drawdowns(total)
    dd_pct = drawdown * 100.0

    fig, (ax_eq, ax_dd) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(10, 8),
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08},
    )

    ax_eq.plot(
        total.index,
        total.values,
        color="#1f77b4",
        linewidth=1.5,
        label="Equity",
    )
    ax_eq.set_title("Portfolio Equity Curve", fontsize=13, fontweight="semibold")
    ax_eq.set_ylabel("Total Value ($)", fontsize=11)
    ax_eq.grid(True, linestyle="--", alpha=0.35)
    ax_eq.legend(loc="upper left", framealpha=0.9)

    x = dd_pct.index
    y = dd_pct.values
    ax_dd.fill_between(
        x,
        y,
        0.0,
        where=(y <= 0),
        color="crimson",
        alpha=0.45,
        interpolate=True,
        label="Drawdown",
    )
    ax_dd.plot(x, y, color="darkred", linewidth=1.0, alpha=0.9)
    ax_dd.set_ylabel("Drawdown", fontsize=11)
    ax_dd.axhline(0.0, color="gray", linewidth=0.8, linestyle="-", alpha=0.6)
    ax_dd.grid(True, linestyle="--", alpha=0.35)
    ax_dd.legend(loc="lower left", framealpha=0.9)

    plt.xlabel("Date", fontsize=11)
    plt.tight_layout()
    plt.show()
