"""
Corridor contracts and configurations.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any


class CorridorLevel(str, Enum):
    """Corridor tightness levels."""
    NORMAL = "normal"       # Standard operating parameters
    WARN = "warn"           # Reduced parallelism, tighter budgets
    TAKEOVER = "takeover"   # Minimal autonomy, maximum stress


@dataclass
class CorridorConfig:
    """
    Dynamic corridor configuration based on presence state.

    max_parallel_tasks: Maximum concurrent tasks
    token_budget: Maximum tokens per operation
    max_tool_calls: Maximum tool calls per turn
    require_approval: Whether to require approval for operations
    taylor_mode_strict: Whether to enforce strict Taylor mode
    """
    max_parallel_tasks: int
    token_budget: int
    max_tool_calls: int
    require_approval: bool
    taylor_mode_strict: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorridorConfig":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def for_level(cls, level: CorridorLevel) -> "CorridorConfig":
        """
        Get default configuration for a corridor level.

        Args:
            level: Corridor level

        Returns:
            CorridorConfig for that level
        """
        if level == CorridorLevel.NORMAL:
            return cls(
                max_parallel_tasks=10,
                token_budget=200000,
                max_tool_calls=50,
                require_approval=False,
                taylor_mode_strict=False,
            )
        elif level == CorridorLevel.WARN:
            return cls(
                max_parallel_tasks=5,
                token_budget=100000,
                max_tool_calls=25,
                require_approval=False,
                taylor_mode_strict=True,
            )
        else:  # TAKEOVER
            return cls(
                max_parallel_tasks=1,
                token_budget=50000,
                max_tool_calls=10,
                require_approval=True,
                taylor_mode_strict=True,
            )


@dataclass
class CorridorStatus:
    """
    Current corridor status.

    level: Current level (normal/warn/takeover)
    config: Current corridor configuration
    metadata: Optional metadata (e.g., last tightening timestamp)
    """
    level: CorridorLevel
    config: CorridorConfig
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "config": self.config.to_dict(),
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorridorStatus":
        """Create from dictionary."""
        return cls(
            level=CorridorLevel(data["level"]),
            config=CorridorConfig.from_dict(data["config"]),
            metadata=data.get("metadata"),
        )
