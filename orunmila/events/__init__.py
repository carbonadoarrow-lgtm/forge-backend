"""Orunmila Events System - Real-time event streaming and routing."""

__version__ = "0.1.0"

from .contracts import (
    EventEnvelope,
    Severity,
    TaylorSummary,
    build_event,
    build_taylor_summary,
)
from .store import EventStore
from .router import EventRouter
from .emitter import EventEmitter

__all__ = [
    "EventEnvelope",
    "Severity",
    "TaylorSummary",
    "build_event",
    "build_taylor_summary",
    "EventStore",
    "EventRouter",
    "EventEmitter",
]
