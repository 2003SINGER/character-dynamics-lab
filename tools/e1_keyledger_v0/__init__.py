"""Finite E1 Key Ledger local-agency development implementation."""

# E0's legacy TypedIR adapter imports its sibling package by the historical
# top-level module name. Make that package discoverable without changing E0.
from pathlib import Path
import sys

_TOOLS = str(Path(__file__).resolve().parents[1])
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
