"""
Presence Tracking System - Monitor founder activity and trigger state transitions.

State machine:
- Normal: Founder active within 24h (business hours)
- Warn: 24h+ since last activity → reduce parallelism, tighten corridors
- Takeover: 48h+ since last activity → minimal autonomy, maximum stress
"""

__version__ = "0.1.0"

from .contracts import PresenceState, ActivityLog
from .clock import BusinessHoursClock
from .state_machine import PresenceStateMachine

__all__ = [
    "PresenceState",
    "ActivityLog",
    "BusinessHoursClock",
    "PresenceStateMachine",
]
