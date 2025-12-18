"""
Event Router - Policy-based event distribution to channels.

Routes events to appropriate channels (Telegram, Cockpit, etc.) based on routing policies.
"""

from dataclasses import dataclass
from typing import Dict, List, Callable, Optional
import logging

from .contracts import EventEnvelope, Severity

logger = logging.getLogger(__name__)


@dataclass
class RoutingRule:
    """
    Rule for routing events to a channel.

    channel: Target channel name (e.g., "telegram", "cockpit")
    event_types: List of event types to match (empty = match all)
    min_severity: Minimum severity level to match
    predicate: Optional custom filter function
    """
    channel: str
    event_types: List[str] = None
    min_severity: Severity = Severity.INFO
    predicate: Optional[Callable[[EventEnvelope], bool]] = None

    def matches(self, event: EventEnvelope) -> bool:
        """
        Check if event matches this rule.

        Args:
            event: Event to check

        Returns:
            True if event matches rule
        """
        # Check severity
        severity_order = {
            Severity.DEBUG: 0,
            Severity.INFO: 1,
            Severity.WARN: 2,
            Severity.ERROR: 3,
            Severity.CRITICAL: 4,
        }
        if severity_order[event.severity] < severity_order[self.min_severity]:
            return False

        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check custom predicate
        if self.predicate and not self.predicate(event):
            return False

        return True


class EventRouter:
    """
    Routes events to channels based on policies.

    - Supports multiple channels (Telegram, Cockpit, etc.)
    - Policy-based routing with severity and type filters
    - Custom predicates for complex routing logic
    """

    def __init__(self):
        """Initialize event router."""
        self.rules: List[RoutingRule] = []
        self.channels: Dict[str, Callable[[EventEnvelope], None]] = {}

    def register_channel(self, channel_name: str, handler: Callable[[EventEnvelope], None]):
        """
        Register a channel handler.

        Args:
            channel_name: Name of the channel
            handler: Function that handles events for this channel
        """
        self.channels[channel_name] = handler
        logger.info(f"Registered channel: {channel_name}")

    def add_rule(self, rule: RoutingRule):
        """
        Add a routing rule.

        Args:
            rule: Routing rule to add
        """
        self.rules.append(rule)
        logger.info(f"Added routing rule: {rule.channel} (types={rule.event_types}, min_severity={rule.min_severity})")

    def route(self, event: EventEnvelope):
        """
        Route event to matching channels.

        Args:
            event: Event to route
        """
        matched_channels = set()

        for rule in self.rules:
            if rule.matches(event):
                matched_channels.add(rule.channel)

        if not matched_channels:
            logger.debug(f"No channels matched for event {event.event_id} (type={event.event_type})")
            return

        logger.debug(f"Routing event {event.event_id} to channels: {matched_channels}")

        for channel_name in matched_channels:
            handler = self.channels.get(channel_name)
            if handler:
                try:
                    handler(event)
                    logger.debug(f"Event {event.event_id} delivered to {channel_name}")
                except Exception as e:
                    logger.error(f"Failed to deliver event {event.event_id} to {channel_name}: {e}")
            else:
                logger.warning(f"No handler registered for channel {channel_name}")

    def remove_rule(self, channel: str, event_type: Optional[str] = None):
        """
        Remove routing rules.

        Args:
            channel: Channel name to remove rules for
            event_type: Optional event type to filter by
        """
        before_count = len(self.rules)
        self.rules = [
            r for r in self.rules
            if not (r.channel == channel and (event_type is None or event_type in (r.event_types or [])))
        ]
        removed = before_count - len(self.rules)
        logger.info(f"Removed {removed} routing rules for channel {channel}")

    def clear_rules(self):
        """Clear all routing rules."""
        count = len(self.rules)
        self.rules = []
        logger.warning(f"Cleared all {count} routing rules")


def load_default_routing_policy(router: EventRouter):
    """
    Load default routing policy.

    Default rules:
    - All WARN+ events → Cockpit
    - All ERROR+ events → Telegram
    - Presence events (warn/takeover) → Telegram
    - Taylor violations → Telegram
    """
    # Cockpit: All WARN+ events
    router.add_rule(RoutingRule(
        channel="cockpit",
        min_severity=Severity.WARN,
    ))

    # Telegram: All ERROR+ events
    router.add_rule(RoutingRule(
        channel="telegram",
        min_severity=Severity.ERROR,
    ))

    # Telegram: Presence warn/takeover events
    router.add_rule(RoutingRule(
        channel="telegram",
        event_types=["presence.warn_threshold", "presence.takeover_threshold"],
        min_severity=Severity.WARN,
    ))

    # Telegram: Taylor violations
    router.add_rule(RoutingRule(
        channel="telegram",
        event_types=["chat.taylor_violation"],
        min_severity=Severity.WARN,
    ))

    logger.info("Loaded default routing policy")
