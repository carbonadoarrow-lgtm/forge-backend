"""
Presence State Machine - Track founder activity and trigger state transitions.

State transitions:
- Normal → Warn: 24h business hours since last activity
- Warn → Takeover: 48h business hours since last activity
- Any → Normal: New activity logged
"""

from pathlib import Path
from typing import Optional
import json
import logging

from .contracts import PresenceState, ActivityLog, PresenceStatus
from .clock import BusinessHoursClock

logger = logging.getLogger(__name__)


class PresenceStateMachine:
    """
    Tracks founder presence and manages state transitions.

    - Logs activity to JSON file
    - Calculates business hours since last activity
    - Triggers state transitions at thresholds
    - Emits events on state changes
    """

    # Thresholds in business hours
    WARN_THRESHOLD = 24.0
    TAKEOVER_THRESHOLD = 48.0

    def __init__(
        self,
        activity_log_path: str = "data/orunmila/presence_activity.json",
        state_path: str = "data/orunmila/presence_state.json",
        event_emitter=None,
    ):
        """
        Initialize presence state machine.

        Args:
            activity_log_path: Path to activity log file
            state_path: Path to state file
            event_emitter: Optional EventEmitter for emitting presence events
        """
        self.activity_log_path = Path(activity_log_path)
        self.state_path = Path(state_path)
        self.event_emitter = event_emitter
        self.clock = BusinessHoursClock()

        self._ensure_files_exist()
        logger.info("PresenceStateMachine initialized")

    def _ensure_files_exist(self):
        """Create state and log files if they don't exist."""
        self.activity_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.activity_log_path.exists():
            # Create initial activity (now)
            initial_activity = ActivityLog.now("system_init")
            self.activity_log_path.write_text(json.dumps([initial_activity.to_dict()], indent=2), encoding="utf-8")

        if not self.state_path.exists():
            # Create initial state (normal)
            initial_state = {
                "state": PresenceState.NORMAL.value,
                "last_transition": ActivityLog.now("system_init").timestamp,
            }
            self.state_path.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    def log_activity(self, activity_type: str, metadata: dict = None):
        """
        Log founder activity.

        Automatically checks for state transition to Normal.

        Args:
            activity_type: Type of activity (e.g., "chat", "code_review")
            metadata: Optional metadata
        """
        activity = ActivityLog.now(activity_type, metadata)

        # Append to activity log
        try:
            with open(self.activity_log_path, "r", encoding="utf-8") as f:
                activities = json.load(f)
        except Exception:
            activities = []

        activities.append(activity.to_dict())

        with open(self.activity_log_path, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2)

        logger.info(f"Logged activity: {activity_type}")

        # Check for state transition to Normal
        current_state = self.get_current_state()
        if current_state != PresenceState.NORMAL:
            self._transition_to_normal()

    def get_last_activity(self) -> ActivityLog:
        """
        Get last logged activity.

        Returns:
            Last activity log
        """
        try:
            with open(self.activity_log_path, "r", encoding="utf-8") as f:
                activities = json.load(f)
            if activities:
                return ActivityLog.from_dict(activities[-1])
        except Exception as e:
            logger.error(f"Failed to read activity log: {e}")

        # Fallback to current time
        return ActivityLog.now("unknown")

    def get_current_state(self) -> PresenceState:
        """
        Get current presence state.

        Returns:
            Current state
        """
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            return PresenceState(state_data["state"])
        except Exception as e:
            logger.error(f"Failed to read state: {e}")
            return PresenceState.NORMAL

    def get_status(self) -> PresenceStatus:
        """
        Get current presence status.

        Returns:
            PresenceStatus with current state, last activity, and hours elapsed
        """
        last_activity = self.get_last_activity()
        current_state = self.get_current_state()
        hours_since_last = self.clock.calculate_business_hours(last_activity.timestamp)

        # Calculate next threshold
        if current_state == PresenceState.NORMAL:
            next_threshold = self.WARN_THRESHOLD - hours_since_last
        elif current_state == PresenceState.WARN:
            next_threshold = self.TAKEOVER_THRESHOLD - hours_since_last
        else:  # TAKEOVER
            next_threshold = 0.0

        return PresenceStatus(
            state=current_state,
            last_activity=last_activity,
            hours_since_last=hours_since_last,
            next_threshold=max(0.0, next_threshold),
        )

    def check_and_transition(self):
        """
        Check thresholds and transition states if needed.

        Should be called periodically (e.g., every hour).
        """
        status = self.get_status()
        current_state = status.state
        hours_since_last = status.hours_since_last

        # Check for state transitions
        if current_state == PresenceState.NORMAL and hours_since_last >= self.WARN_THRESHOLD:
            self._transition_to_warn(hours_since_last)
        elif current_state == PresenceState.WARN and hours_since_last >= self.TAKEOVER_THRESHOLD:
            self._transition_to_takeover(hours_since_last)

    def _transition_to_normal(self):
        """Transition to Normal state."""
        self._set_state(PresenceState.NORMAL)
        logger.info("Presence state → NORMAL")

    def _transition_to_warn(self, hours_since_last: float):
        """Transition to Warn state."""
        self._set_state(PresenceState.WARN)
        logger.warning(f"Presence state → WARN (24h threshold reached, {hours_since_last:.1f}h elapsed)")

        # Emit event
        if self.event_emitter:
            self.event_emitter.emit_presence_warn(hours_since_last)

    def _transition_to_takeover(self, hours_since_last: float):
        """Transition to Takeover state."""
        self._set_state(PresenceState.TAKEOVER)
        logger.error(f"Presence state → TAKEOVER (48h threshold reached, {hours_since_last:.1f}h elapsed)")

        # Emit event
        if self.event_emitter:
            self.event_emitter.emit_presence_takeover(hours_since_last)

    def _set_state(self, state: PresenceState):
        """
        Set current state.

        Args:
            state: New state
        """
        state_data = {
            "state": state.value,
            "last_transition": ActivityLog.now("state_transition").timestamp,
        }
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def force_state(self, state: PresenceState):
        """
        Force a state transition (for testing/manual override).

        Args:
            state: State to force
        """
        self._set_state(state)
        logger.warning(f"Force set presence state to {state.value}")
