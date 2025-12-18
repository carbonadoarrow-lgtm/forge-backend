"""
Corridor Manager - Dynamically adjust constraints based on presence state.

Automatically tightens corridors when founder is away.
"""

from pathlib import Path
from datetime import datetime
import json
import logging

from .contracts import CorridorLevel, CorridorConfig, CorridorStatus
from ..presence.contracts import PresenceState

logger = logging.getLogger(__name__)


class CorridorManager:
    """
    Manages dynamic corridor configuration.

    - Syncs corridor level with presence state
    - Persists configuration to disk
    - Provides configuration queries for LLM operations
    """

    def __init__(
        self,
        config_path: str = "data/orunmila/corridors.json",
        presence_state_machine=None,
    ):
        """
        Initialize corridor manager.

        Args:
            config_path: Path to corridors config file
            presence_state_machine: Optional PresenceStateMachine for auto-sync
        """
        self.config_path = Path(config_path)
        self.presence_state_machine = presence_state_machine

        self._ensure_config_exists()
        logger.info("CorridorManager initialized")

    def _ensure_config_exists(self):
        """Create config file if it doesn't exist."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            # Create initial config (normal level)
            initial_status = CorridorStatus(
                level=CorridorLevel.NORMAL,
                config=CorridorConfig.for_level(CorridorLevel.NORMAL),
                metadata={"last_update": datetime.utcnow().isoformat()},
            )
            self.config_path.write_text(json.dumps(initial_status.to_dict(), indent=2), encoding="utf-8")

    def get_current_status(self) -> CorridorStatus:
        """
        Get current corridor status.

        Returns:
            Current corridor status
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CorridorStatus.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to read corridor config: {e}")
            # Return default
            return CorridorStatus(
                level=CorridorLevel.NORMAL,
                config=CorridorConfig.for_level(CorridorLevel.NORMAL),
            )

    def get_current_config(self) -> CorridorConfig:
        """
        Get current corridor configuration.

        Returns:
            Current corridor config
        """
        return self.get_current_status().config

    def sync_with_presence(self):
        """
        Sync corridor level with current presence state.

        Should be called after presence state transitions.
        """
        if not self.presence_state_machine:
            logger.warning("No presence state machine configured")
            return

        presence_state = self.presence_state_machine.get_current_state()

        # Map presence state to corridor level
        if presence_state == PresenceState.NORMAL:
            target_level = CorridorLevel.NORMAL
        elif presence_state == PresenceState.WARN:
            target_level = CorridorLevel.WARN
        else:  # TAKEOVER
            target_level = CorridorLevel.TAKEOVER

        current_status = self.get_current_status()

        if current_status.level != target_level:
            self.set_level(target_level)
            logger.info(f"Synced corridors with presence: {target_level.value}")

    def set_level(self, level: CorridorLevel):
        """
        Set corridor level.

        Args:
            level: New corridor level
        """
        config = CorridorConfig.for_level(level)
        status = CorridorStatus(
            level=level,
            config=config,
            metadata={"last_update": datetime.utcnow().isoformat()},
        )

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(status.to_dict(), f, indent=2)

        logger.info(f"Corridor level set to {level.value}")

    def set_custom_config(self, config: CorridorConfig, level: CorridorLevel = CorridorLevel.NORMAL):
        """
        Set custom corridor configuration.

        Args:
            config: Custom corridor configuration
            level: Corridor level to associate with
        """
        status = CorridorStatus(
            level=level,
            config=config,
            metadata={"last_update": datetime.utcnow().isoformat(), "custom": True},
        )

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(status.to_dict(), f, indent=2)

        logger.info(f"Custom corridor config set for level {level.value}")

    def check_operation_allowed(self, operation: str, **kwargs) -> bool:
        """
        Check if an operation is allowed under current corridors.

        Args:
            operation: Operation type (e.g., "parallel_tasks", "tool_call")
            **kwargs: Operation parameters (e.g., count=5)

        Returns:
            True if allowed, False if blocked
        """
        config = self.get_current_config()

        if operation == "parallel_tasks":
            count = kwargs.get("count", 1)
            return count <= config.max_parallel_tasks

        elif operation == "tool_call":
            total_calls = kwargs.get("total_calls", 1)
            return total_calls <= config.max_tool_calls

        elif operation == "token_usage":
            tokens = kwargs.get("tokens", 0)
            return tokens <= config.token_budget

        elif operation == "requires_approval":
            return not config.require_approval

        else:
            logger.warning(f"Unknown operation type: {operation}")
            return True  # Allow by default

    def get_remaining_budget(self, operation: str, current_usage: int) -> int:
        """
        Get remaining budget for an operation.

        Args:
            operation: Operation type
            current_usage: Current usage amount

        Returns:
            Remaining budget
        """
        config = self.get_current_config()

        if operation == "parallel_tasks":
            return max(0, config.max_parallel_tasks - current_usage)
        elif operation == "tool_calls":
            return max(0, config.max_tool_calls - current_usage)
        elif operation == "tokens":
            return max(0, config.token_budget - current_usage)
        else:
            return 0
