"""
Presence contracts and data structures.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any


class PresenceState(str, Enum):
    """Presence state levels."""
    NORMAL = "normal"       # Founder active within 24h
    WARN = "warn"           # 24h+ since last activity
    TAKEOVER = "takeover"   # 48h+ since last activity


@dataclass
class ActivityLog:
    """
    Record of founder activity.

    timestamp: ISO 8601 timestamp of activity
    activity_type: Type of activity (e.g., "chat", "code_review", "manual_trigger")
    metadata: Optional metadata (user agent, IP, etc.)
    """
    timestamp: str
    activity_type: str
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLog":
        """Create from dictionary."""
        return cls(
            timestamp=data["timestamp"],
            activity_type=data["activity_type"],
            metadata=data.get("metadata"),
        )

    @classmethod
    def now(cls, activity_type: str, metadata: Dict[str, Any] = None) -> "ActivityLog":
        """Create activity log with current timestamp."""
        return cls(
            timestamp=datetime.utcnow().isoformat(),
            activity_type=activity_type,
            metadata=metadata or {},
        )


@dataclass
class PresenceStatus:
    """
    Current presence status.

    state: Current state (normal/warn/takeover)
    last_activity: Last activity log
    hours_since_last: Business hours since last activity
    next_threshold: Hours until next state transition
    """
    state: PresenceState
    last_activity: ActivityLog
    hours_since_last: float
    next_threshold: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "last_activity": self.last_activity.to_dict(),
            "hours_since_last": self.hours_since_last,
            "next_threshold": self.next_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PresenceStatus":
        """Create from dictionary."""
        return cls(
            state=PresenceState(data["state"]),
            last_activity=ActivityLog.from_dict(data["last_activity"]),
            hours_since_last=data["hours_since_last"],
            next_threshold=data["next_threshold"],
        )
