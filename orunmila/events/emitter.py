"""
Event Emitter - High-level interface for emitting events.

Combines EventStore and EventRouter for easy event emission with automatic persistence and routing.
"""

from typing import List, Optional, Dict, Any
import logging

from .contracts import EventEnvelope, Severity, build_event
from .store import EventStore
from .router import EventRouter, load_default_routing_policy

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    High-level event emission interface.

    - Automatically persists events to store
    - Routes events to channels via router
    - Provides convenience methods for common event types
    """

    def __init__(
        self,
        store_path: str = "data/orunmila/events.jsonl",
        use_default_policy: bool = True,
    ):
        """
        Initialize event emitter.

        Args:
            store_path: Path to event store
            use_default_policy: Whether to load default routing policy
        """
        self.store = EventStore(store_path)
        self.router = EventRouter()

        if use_default_policy:
            load_default_routing_policy(self.router)

        logger.info("EventEmitter initialized")

    def emit(self, event: EventEnvelope):
        """
        Emit an event.

        Persists to store and routes to channels.

        Args:
            event: Event to emit
        """
        try:
            # Persist to store
            self.store.append(event)

            # Route to channels
            self.router.route(event)

            logger.info(f"Emitted event {event.event_id} (type={event.event_type}, severity={event.severity})")

        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
            raise

    def emit_simple(
        self,
        event_type: str,
        severity: Severity,
        observation: str,
        implication: str,
        constraints: List[str],
        choice_set: List[str],
        meta_clarifier: str = "",
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Emit a simple event using build_event helper.

        Args:
            event_type: Event type (domain.action format)
            severity: Severity level
            observation: What happened
            implication: What it means
            constraints: What limits our response
            choice_set: Available actions
            meta_clarifier: Context/nuance
            payload: Optional raw data
            metadata: Optional metadata
        """
        event = build_event(
            event_type=event_type,
            severity=severity,
            observation=observation,
            implication=implication,
            constraints=constraints,
            choice_set=choice_set,
            meta_clarifier=meta_clarifier,
            payload=payload,
            metadata=metadata,
        )
        self.emit(event)

    def emit_presence_warn(self, hours_since_last: float):
        """
        Emit presence warning event (24h threshold).

        Args:
            hours_since_last: Hours since last founder activity
        """
        self.emit_simple(
            event_type="presence.warn_threshold",
            severity=Severity.WARN,
            observation=f"Founder last active {hours_since_last:.1f} hours ago (24h warning threshold reached)",
            implication="System entering warn state - reduced parallelism, tightened corridors",
            constraints=["Must respect business hours", "Cannot force founder interaction"],
            choice_set=[
                "Continue monitoring",
                "Send gentle notification",
                "Prepare for takeover state",
            ],
            meta_clarifier="Weekends excluded from calculation",
            payload={"hours_since_last": hours_since_last},
        )

    def emit_presence_takeover(self, hours_since_last: float):
        """
        Emit presence takeover event (48h threshold).

        Args:
            hours_since_last: Hours since last founder activity
        """
        self.emit_simple(
            event_type="presence.takeover_threshold",
            severity=Severity.ERROR,
            observation=f"Founder last active {hours_since_last:.1f} hours ago (48h takeover threshold reached)",
            implication="System entering takeover state - minimal parallelism, maximum stress tightening",
            constraints=["Must respect business hours", "Cannot make irreversible decisions"],
            choice_set=[
                "Continue with reduced autonomy",
                "Send urgent notification",
                "Prepare return brief",
            ],
            meta_clarifier="Weekends excluded from calculation",
            payload={"hours_since_last": hours_since_last},
        )

    def emit_taylor_violation(self, message: str, violations: List[str]):
        """
        Emit Taylor mode violation event.

        Args:
            message: The violating message
            violations: List of violations detected
        """
        self.emit_simple(
            event_type="chat.taylor_violation",
            severity=Severity.WARN,
            observation=f"Taylor mode violation detected: {', '.join(violations)}",
            implication="Response blocked - Taylor compliance required",
            constraints=["Must use 5-slot structure", "No forbidden phrases", "No claims of understanding"],
            choice_set=[
                "Regenerate compliant response",
                "Log violation for neuroplasticity",
                "Notify operator",
            ],
            meta_clarifier="Hardened mode for critical operations",
            payload={"message": message, "violations": violations},
        )

    def emit_neuroplasticity_update(self, intent: str, applied: bool, reason: str = ""):
        """
        Emit neuroplasticity update event.

        Args:
            intent: The distilled intent
            applied: Whether intent was applied
            reason: Reason for decision
        """
        self.emit_simple(
            event_type="neuroplasticity.update_applied" if applied else "neuroplasticity.update_rejected",
            severity=Severity.INFO,
            observation=f"Neuroplasticity intent: {intent}",
            implication=f"Intent {'applied to config' if applied else 'rejected'}",
            constraints=["Must be unambiguous", "Must be safe", "Must be reversible"],
            choice_set=[
                "Apply to config",
                "Log for manual review",
                "Discard",
            ],
            meta_clarifier=reason or "Automatic application from clear intent",
            payload={"intent": intent, "applied": applied, "reason": reason},
        )

    def get_recent_events(self, limit: int = 100) -> List[EventEnvelope]:
        """
        Get recent events from store.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events (newest first)
        """
        return self.store.read_recent(limit)

    def get_events_by_type(self, event_type: str) -> List[EventEnvelope]:
        """
        Get events by type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of matching events
        """
        return self.store.read_by_type(event_type)
