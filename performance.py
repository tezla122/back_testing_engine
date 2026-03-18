"""
Performance metrics and drawdown statistics for backtests.

Provides annualized Sharpe-style ratios (zero risk-free rate) and
peak-to-trough drawdown analysis on equity curves.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def create_sharpe_ratio(returns: pd.Series, periods: int = 252) -> float:
    """
    Annualized Sharpe ratio assuming a zero risk-free rate.

    Uses the sample standard deviation (``ddof=1``) to match typical
    pandas conventions. Never raises for bad input; returns ``0.0`` when
    the ratio is undefined (empty returns, zero variance, non-finite
    values, invalid ``periods``).

    .. math::

        \\text{Sharpe} = \\sqrt{\\text{periods}} \\times
        \\frac{\\mu}{\\sigma}

    Parameters
    ----------
    returns:
        Period-over-period returns (e.g. daily). May contain NaN; any
        non-numeric values are coerced or dropped.
    periods:
        Number of return periods per year for annualization (default
        252 trading days). Must be positive and finite.

    Returns
    -------
    float
        Annualized Sharpe ratio, or ``0.0`` if undefined.
    """
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
    """
    Compute running drawdowns from an equity curve.

    High water mark is the cumulative maximum of equity. Drawdown at
    each point is ``(equity - HWM) / HWM``. Where HWM is zero, drawdown
    is set to 0.0 to avoid division by zero.

    The **longest drawdown duration** is the maximum number of
    consecutive periods where equity is strictly below the running
    maximum (i.e. still underwater relative to the prior peak).

    Parameters
    ----------
    equity_curve:
        Portfolio value through time. Index may be dates or integers.

    Returns
    -------
    tuple[pd.Series, float, float]
        * Drawdown series (same index as ``equity_curve``).
        * Maximum drawdown (most negative value, or 0.0 if none).
        * Longest drawdown duration in **periods** (as float).
    """
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
