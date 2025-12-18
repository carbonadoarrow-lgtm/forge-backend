"""
Communication Guard - Enforce Taylor mode compliance.

Validates that LLM responses follow Taylor's 5-slot structure and forbidden phrase rules.
"""

__version__ = "0.1.0"

from .validator import CommunicationGuard, TaylorViolation

__all__ = [
    "CommunicationGuard",
    "TaylorViolation",
]
