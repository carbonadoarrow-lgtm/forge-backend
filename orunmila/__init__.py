"""
Orunmila - Advanced LLM Runtime Management system for Forge OS.

Provides:
- Events: Real-time event streaming and routing
- Presence: Founder activity tracking with state machine
- Communication Guard: Taylor mode compliance validation
- Corridors: Dynamic constraint system
- Neuroplasticity: Episode logging and auto-application
"""

__version__ = "0.1.0"

from .events import (
    EventEmitter,
    EventEnvelope,
    Severity,
    build_event,
)

__all__ = [
    "EventEmitter",
    "EventEnvelope",
    "Severity",
    "build_event",
]
