"""
Corridors - Dynamic constraint system that tightens based on presence state.

Provides context-aware boundaries for LLM operations:
- Normal state: Standard corridors
- Warn state: Reduced parallelism, tighter token budgets
- Takeover state: Minimal autonomy, maximum stress tightening
"""

__version__ = "0.1.0"

from .contracts import CorridorConfig, CorridorLevel
from .manager import CorridorManager

__all__ = [
    "CorridorConfig",
    "CorridorLevel",
    "CorridorManager",
]
