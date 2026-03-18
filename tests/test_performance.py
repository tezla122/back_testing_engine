"""
Unit tests for performance metrics (Sharpe, drawdowns).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from performance import create_drawdowns, create_sharpe_ratio


def test_create_sharpe_ratio_expected_value() -> None:
    """
    Series with mean 0.001 and sample std 0.002 (ddof=1): Sharpe annualized.
    Two points: spread 0.02 * sqrt(2) gives std = 0.02.
    """
    lo = 0.001 - 0.01 * math.sqrt(2)
    hi = 0.001 + 0.01 * math.sqrt(2)
    returns = pd.Series([lo, hi])
    assert returns.mean() == pytest.approx(0.001)
    assert returns.std(ddof=1) == pytest.approx(0.02)

    expected = math.sqrt(252) * (0.001 / 0.02)
    assert create_sharpe_ratio(returns, periods=252) == pytest.approx(expected)


def test_create_sharpe_ratio_empty_or_zero_std() -> None:
    """Empty or constant returns yield 0.0."""
    assert create_sharpe_ratio(pd.Series([], dtype=float)) == 0.0
    assert create_sharpe_ratio(pd.Series([0.01, 0.01, 0.01])) == 0.0


def test_create_drawdowns_max_drawdown() -> None:
    """
    Peak 120, subsequent low 80 => max DD (80 - 120) / 120 = -1/3.
    """
    equity = pd.Series([100, 120, 90, 100, 80, 150])
    dd_series, max_dd, duration = create_drawdowns(equity)

    assert len(dd_series) == len(equity)
    assert max_dd == pytest.approx(-1.0 / 3.0, rel=1e-4)
    # Underwater from bar after peak until new high: 3 consecutive periods.
    assert duration == pytest.approx(3.0)


def test_create_drawdowns_empty() -> None:
    empty = pd.Series([], dtype=float)
    dd, mdd, dur = create_drawdowns(empty)
    assert len(dd) == 0
    assert mdd == 0.0
    assert dur == 0.0
