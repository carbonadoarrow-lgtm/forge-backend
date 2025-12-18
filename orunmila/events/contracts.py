"""
Event contracts for Orunmila Events System.

Defines the structure of events flowing through the system with Taylor-compliant summaries.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class Severity(str, Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TaylorSummary:
    """
    Taylor-compliant 5-slot event summary structure.

    observation: What happened (factual)
    implication: What it means (inference)
    constraints: What limits our response (boundaries)
    choice_set: Available actions (options)
    meta_clarifier: Context/nuance (additional info)
    """
    observation: str
    implication: str
    constraints: List[str]
    choice_set: List[str]
    meta_clarifier: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaylorSummary":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class EventEnvelope:
    """
    Universal event envelope for all Orunmila events.

    Every event has:
    - Unique ID
    - Timestamp
    - Type (domain.action format)
    - Severity
    - Taylor summary (5-slot structure)
    - Optional payload (raw data)
    - Optional metadata (tags, context)
    """
    event_id: str
    timestamp: str  # ISO 8601
    event_type: str  # e.g., "presence.warn_threshold", "chat.taylor_violation"
    severity: Severity
    taylor_summary: TaylorSummary
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "taylor_summary": self.taylor_summary.to_dict(),
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventEnvelope":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            severity=Severity(data["severity"]),
            taylor_summary=TaylorSummary.from_dict(data["taylor_summary"]),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )

    def to_json_line(self) -> str:
        """Convert to JSON string (for JSONL storage)."""
        import json
        return json.dumps(self.to_dict())

    @classmethod
    def from_json_line(cls, line: str) -> "EventEnvelope":
        """Create from JSON string."""
        import json
        return cls.from_dict(json.loads(line))


def build_event(
    event_type: str,
    severity: Severity,
    observation: str,
    implication: str,
    constraints: List[str],
    choice_set: List[str],
    meta_clarifier: str = "",
    payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EventEnvelope:
    """
    Build an event with Taylor summary.

    Args:
        event_type: Event type (domain.action format)
        severity: Severity level
        observation: What happened (factual)
        implication: What it means (inference)
        constraints: What limits our response
        choice_set: Available actions
        meta_clarifier: Context/nuance
        payload: Optional raw data
        metadata: Optional metadata (tags, context)

    Returns:
        EventEnvelope ready to emit
    """
    return EventEnvelope(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        event_type=event_type,
        severity=severity,
        taylor_summary=TaylorSummary(
            observation=observation,
            implication=implication,
            constraints=constraints,
            choice_set=choice_set,
            meta_clarifier=meta_clarifier,
        ),
        payload=payload or {},
        metadata=metadata or {},
    )


def build_taylor_summary(
    observation: str,
    implication: str,
    constraints: List[str],
    choice_set: List[str],
    meta_clarifier: str = "",
) -> TaylorSummary:
    """
    Build a standalone Taylor summary.

    Args:
        observation: What happened (factual)
        implication: What it means (inference)
        constraints: What limits our response
        choice_set: Available actions
        meta_clarifier: Context/nuance

    Returns:
        TaylorSummary instance
    """
    return TaylorSummary(
        observation=observation,
        implication=implication,
        constraints=constraints,
        choice_set=choice_set,
        meta_clarifier=meta_clarifier,
    )
