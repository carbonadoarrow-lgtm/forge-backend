"""
Episode Logger - Records interaction episodes for neuroplasticity.
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import uuid
import logging

from .contracts import Episode, EpisodeType

logger = logging.getLogger(__name__)


class EpisodeLogger:
    """
    Logs interaction episodes to JSONL file.

    - Append-only logging
    - One episode per line
    - Automatic file creation
    """

    def __init__(self, log_path: str = "data/orunmila/episodes.jsonl"):
        """
        Initialize episode logger.

        Args:
            log_path: Path to episodes log file
        """
        self.log_path = Path(log_path)
        self._ensure_log_exists()
        logger.info(f"EpisodeLogger initialized: {log_path}")

    def _ensure_log_exists(self):
        """Create log file if it doesn't exist."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def log_episode(
        self,
        episode_type: EpisodeType,
        context: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> Episode:
        """
        Log an episode.

        Args:
            episode_type: Type of episode
            context: Context data
            metadata: Optional metadata

        Returns:
            Logged episode
        """
        episode = Episode.now(
            episode_id=str(uuid.uuid4()),
            episode_type=episode_type,
            context=context,
            metadata=metadata,
        )

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode.to_dict()) + "\n")
            logger.debug(f"Logged episode {episode.episode_id} (type={episode_type})")
        except Exception as e:
            logger.error(f"Failed to log episode: {e}")
            raise

        return episode

    def read_all_episodes(self) -> List[Episode]:
        """
        Read all episodes from log.

        Returns:
            List of episodes (oldest first)
        """
        episodes = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            episode = Episode.from_dict(json.loads(line))
                            episodes.append(episode)
                        except Exception as e:
                            logger.warning(f"Failed to parse episode line: {e}")
        except FileNotFoundError:
            logger.warning(f"Episode log not found: {self.log_path}")
        except Exception as e:
            logger.error(f"Failed to read episodes: {e}")

        return episodes

    def read_recent_episodes(self, limit: int = 100) -> List[Episode]:
        """
        Read recent episodes.

        Args:
            limit: Maximum number of episodes to return

        Returns:
            List of episodes (newest first)
        """
        all_episodes = self.read_all_episodes()
        return list(reversed(all_episodes[-limit:]))

    def read_episodes_by_type(self, episode_type: EpisodeType) -> List[Episode]:
        """
        Read episodes by type.

        Args:
            episode_type: Episode type to filter by

        Returns:
            List of matching episodes
        """
        all_episodes = self.read_all_episodes()
        return [e for e in all_episodes if e.episode_type == episode_type]

    def count_episodes(self) -> int:
        """
        Count total episodes.

        Returns:
            Total episode count
        """
        return len(self.read_all_episodes())

    def clear_log(self):
        """
        Clear all episodes.

        WARNING: This is destructive and cannot be undone.
        """
        try:
            self.log_path.write_text("", encoding="utf-8")
            logger.warning(f"Cleared episode log: {self.log_path}")
        except Exception as e:
            logger.error(f"Failed to clear episode log: {e}")
            raise
