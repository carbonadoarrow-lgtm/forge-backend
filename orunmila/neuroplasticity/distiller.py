"""
Intent Distiller - Extract clear intents from episodes.

Analyzes episodes to identify unambiguous configuration changes.
"""

from typing import List, Optional, Dict, Any
import uuid
import logging

from .contracts import Episode, Intent, IntentStatus, EpisodeType

logger = logging.getLogger(__name__)


class IntentDistiller:
    """
    Distills intents from episodes.

    - Looks for clear, unambiguous preferences
    - Assigns confidence scores
    - Creates config patches for auto-application
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8  # Auto-apply
    MEDIUM_CONFIDENCE_THRESHOLD = 0.5  # Manual review
    LOW_CONFIDENCE_THRESHOLD = 0.3  # Log only

    def __init__(self, auto_apply_threshold: float = 0.8):
        """
        Initialize intent distiller.

        Args:
            auto_apply_threshold: Confidence threshold for auto-application
        """
        self.auto_apply_threshold = auto_apply_threshold
        logger.info(f"IntentDistiller initialized (auto_apply_threshold={auto_apply_threshold})")

    def distill_from_episodes(self, episodes: List[Episode]) -> List[Intent]:
        """
        Distill intents from episodes.

        Args:
            episodes: List of episodes to analyze

        Returns:
            List of distilled intents
        """
        intents = []

        # Group episodes by type
        correction_episodes = [e for e in episodes if e.episode_type == EpisodeType.CORRECTION]
        preference_episodes = [e for e in episodes if e.episode_type == EpisodeType.PREFERENCE]

        # Process corrections
        for episode in correction_episodes:
            intent = self._extract_correction_intent(episode)
            if intent:
                intents.append(intent)

        # Process preferences
        for episode in preference_episodes:
            intent = self._extract_preference_intent(episode)
            if intent:
                intents.append(intent)

        logger.info(f"Distilled {len(intents)} intents from {len(episodes)} episodes")
        return intents

    def _extract_correction_intent(self, episode: Episode) -> Optional[Intent]:
        """
        Extract intent from correction episode.

        Args:
            episode: Correction episode

        Returns:
            Intent if extractable, None otherwise
        """
        context = episode.context

        # Check if correction contains clear intent
        correction_text = context.get("correction", "")
        if not correction_text:
            return None

        # Simple keyword-based extraction (can be enhanced with LLM)
        keywords = ["always", "never", "must", "should not", "prefer"]
        has_clear_directive = any(kw in correction_text.lower() for kw in keywords)

        if not has_clear_directive:
            return None

        # Create intent
        confidence = 0.7  # Medium-high for explicit corrections
        description = f"Correction: {correction_text[:100]}"

        return Intent.now(
            intent_id=str(uuid.uuid4()),
            description=description,
            source_episodes=[episode.episode_id],
            confidence=confidence,
            status=IntentStatus.PENDING,
            metadata={"extraction_method": "keyword"},
        )

    def _extract_preference_intent(self, episode: Episode) -> Optional[Intent]:
        """
        Extract intent from preference episode.

        Args:
            episode: Preference episode

        Returns:
            Intent if extractable, None otherwise
        """
        context = episode.context

        # Check if preference is clear
        preference_text = context.get("preference", "")
        if not preference_text:
            return None

        # Check for config-related keywords
        config_keywords = ["config", "setting", "parameter", "corridor", "threshold"]
        is_config_related = any(kw in preference_text.lower() for kw in config_keywords)

        if not is_config_related:
            return None

        # Create intent
        confidence = 0.6  # Medium for preferences
        description = f"Preference: {preference_text[:100]}"

        return Intent.now(
            intent_id=str(uuid.uuid4()),
            description=description,
            source_episodes=[episode.episode_id],
            confidence=confidence,
            status=IntentStatus.PENDING,
            metadata={"extraction_method": "keyword"},
        )

    def should_auto_apply(self, intent: Intent) -> bool:
        """
        Check if intent should be auto-applied.

        Args:
            intent: Intent to check

        Returns:
            True if should auto-apply
        """
        return intent.confidence >= self.auto_apply_threshold

    def create_config_patch(self, intent: Intent) -> Optional[Dict[str, Any]]:
        """
        Create config patch from intent.

        This is a simplified version - in production, this would use
        an LLM to generate the actual config patch.

        Args:
            intent: Intent to create patch for

        Returns:
            Config patch if creatable, None otherwise
        """
        # Placeholder for actual LLM-based patch generation
        # In v1, we return None and require manual patching
        logger.debug(f"Config patch generation not implemented for intent {intent.intent_id}")
        return None

    def merge_similar_intents(self, intents: List[Intent]) -> List[Intent]:
        """
        Merge similar intents to reduce noise.

        Args:
            intents: List of intents

        Returns:
            Merged intents
        """
        # Placeholder for actual similarity detection and merging
        # In v1, we just return the input list
        return intents
