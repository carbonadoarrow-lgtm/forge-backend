"""
Neuroplasticity contracts and data structures.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class EpisodeType(str, Enum):
    """Types of episodes."""
    CHAT = "chat"
    CODE_REVIEW = "code_review"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    OTHER = "other"


class IntentStatus(str, Enum):
    """Status of distilled intents."""
    PENDING = "pending"         # Not yet reviewed
    APPROVED = "approved"       # Approved for application
    APPLIED = "applied"         # Applied to config
    REJECTED = "rejected"       # Rejected (ambiguous or unsafe)


@dataclass
class Episode:
    """
    Record of an interaction episode.

    episode_id: Unique episode ID
    timestamp: ISO 8601 timestamp
    episode_type: Type of episode
    context: Context data (e.g., user message, response)
    metadata: Optional metadata
    """
    episode_id: str
    timestamp: str
    episode_type: EpisodeType
    context: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "episode_id": self.episode_id,
            "timestamp": self.timestamp,
            "episode_type": self.episode_type.value,
            "context": self.context,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        """Create from dictionary."""
        return cls(
            episode_id=data["episode_id"],
            timestamp=data["timestamp"],
            episode_type=EpisodeType(data["episode_type"]),
            context=data["context"],
            metadata=data.get("metadata"),
        )

    @classmethod
    def now(
        cls,
        episode_id: str,
        episode_type: EpisodeType,
        context: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> "Episode":
        """Create episode with current timestamp."""
        return cls(
            episode_id=episode_id,
            timestamp=datetime.utcnow().isoformat(),
            episode_type=episode_type,
            context=context,
            metadata=metadata,
        )


@dataclass
class Intent:
    """
    Distilled intent from episodes.

    intent_id: Unique intent ID
    timestamp: ISO 8601 timestamp
    description: Human-readable intent description
    source_episodes: Episode IDs that led to this intent
    confidence: Confidence score (0.0-1.0)
    status: Current status
    config_patch: Optional config patch to apply
    metadata: Optional metadata
    """
    intent_id: str
    timestamp: str
    description: str
    source_episodes: List[str]
    confidence: float
    status: IntentStatus
    config_patch: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent_id": self.intent_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "source_episodes": self.source_episodes,
            "confidence": self.confidence,
            "status": self.status.value,
            "config_patch": self.config_patch,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """Create from dictionary."""
        return cls(
            intent_id=data["intent_id"],
            timestamp=data["timestamp"],
            description=data["description"],
            source_episodes=data["source_episodes"],
            confidence=data["confidence"],
            status=IntentStatus(data["status"]),
            config_patch=data.get("config_patch"),
            metadata=data.get("metadata"),
        )

    @classmethod
    def now(
        cls,
        intent_id: str,
        description: str,
        source_episodes: List[str],
        confidence: float,
        status: IntentStatus = IntentStatus.PENDING,
        config_patch: Optional[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
    ) -> "Intent":
        """Create intent with current timestamp."""
        return cls(
            intent_id=intent_id,
            timestamp=datetime.utcnow().isoformat(),
            description=description,
            source_episodes=source_episodes,
            confidence=confidence,
            status=status,
            config_patch=config_patch,
            metadata=metadata,
        )
