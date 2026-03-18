"""Pytest configuration: allow imports from the tests directory."""

from __future__ import annotations

import sys
from pathlib import Path

_tests_dir = Path(__file__).resolve().parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))
