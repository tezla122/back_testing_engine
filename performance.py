

from __future__ import annotations

import numpy as np
import pandas as pd


def create_sharpe_ratio(returns: pd.Series, periods: int = 252) -> float:
   
    try:
        if returns is None:
            return 0.0
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
        if len(returns) == 0:
            return 0.0

        if (
            not np.isfinite(periods)
            or periods <= 0
            or isinstance(periods, (bool, np.bool_))
        ):
            return 0.0

        r = pd.to_numeric(returns, errors="coerce").dropna()
        if len(r) == 0:
            return 0.0
        if len(r) < 2:
            return 0.0

        mean = float(r.mean())
        std = float(r.std(ddof=1))
        if not np.isfinite(mean):
            return 0.0
        if not np.isfinite(std) or std == 0.0 or np.isclose(std, 0.0):
            return 0.0

        ratio = float(np.sqrt(float(periods)) * (mean / std))
        if not np.isfinite(ratio):
            return 0.0
        return ratio
    except (TypeError, ValueError, ZeroDivisionError, FloatingPointError):
        return 0.0


def create_drawdowns(
    equity_curve: pd.Series,
) -> tuple[pd.Series, float, float]:
   
    if equity_curve is None or len(equity_curve) == 0:
        empty = pd.Series(dtype=float)
        return empty, 0.0, 0.0

    equity = pd.to_numeric(equity_curve, errors="coerce").astype(float)
    running_max = equity.cummax()
    denom = running_max.replace(0.0, np.nan)
    drawdown = (equity - running_max) / denom
    drawdown = drawdown.fillna(0.0)

    max_dd = float(drawdown.min()) if len(drawdown) else 0.0
    if not np.isfinite(max_dd):
        max_dd = 0.0

    underwater = equity < running_max
    max_duration = 0
    current = 0
    for u in underwater.to_numpy(dtype=bool):
        if u:
            current += 1
            if current > max_duration:
                max_duration = current
        else:
            current = 0

    return drawdown, max_dd, float(max_duration)
