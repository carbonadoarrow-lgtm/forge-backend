"""
Event Store - JSONL-based append-only event log.

Stores events to disk in newline-delimited JSON format for durability and replayability.
"""

from pathlib import Path
from typing import List, Optional
import logging

from .contracts import EventEnvelope

logger = logging.getLogger(__name__)


class EventStore:
    """
    JSONL-based event storage.

    - Append-only writes (no updates/deletes)
    - One event per line
    - Automatic file creation
    - Thread-safe appending
    """

    def __init__(self, store_path: str = "data/orunmila/events.jsonl"):
        """
        Initialize event store.

        Args:
            store_path: Path to JSONL file
        """
        self.store_path = Path(store_path)
        self._ensure_store_exists()

    def _ensure_store_exists(self):
        """Create store directory and file if they don't exist."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.touch()
            logger.info(f"Created event store at {self.store_path}")

    def append(self, event: EventEnvelope):
        """
        Append event to store.

        Args:
            event: Event to append
        """
        try:
            with open(self.store_path, "a", encoding="utf-8") as f:
                f.write(event.to_json_line() + "\n")
            logger.debug(f"Appended event {event.event_id} to store")
        except Exception as e:
            logger.error(f"Failed to append event {event.event_id}: {e}")
            raise

    def read_all(self) -> List[EventEnvelope]:
        """
        Read all events from store.

        Returns:
            List of events (oldest first)
        """
        events = []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = EventEnvelope.from_json_line(line)
                            events.append(event)
                        except Exception as e:
                            logger.warning(f"Failed to parse event line: {e}")
        except FileNotFoundError:
            logger.warning(f"Event store not found at {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to read events: {e}")
            raise
        return events

    def read_recent(self, limit: int = 100) -> List[EventEnvelope]:
        """
        Read most recent events from store.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of events (newest first)
        """
        all_events = self.read_all()
        return list(reversed(all_events[-limit:]))

    def read_by_type(self, event_type: str) -> List[EventEnvelope]:
        """
        Read events by type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of matching events (oldest first)
        """
        all_events = self.read_all()
        return [e for e in all_events if e.event_type == event_type]

    def read_by_severity(self, severity: str) -> List[EventEnvelope]:
        """
        Read events by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of matching events (oldest first)
        """
        all_events = self.read_all()
        return [e for e in all_events if e.severity.value == severity]

    def count(self) -> int:
        """
        Count total events in store.

        Returns:
            Total event count
        """
        return len(self.read_all())

    def clear(self):
        """
        Clear all events from store.

        WARNING: This is destructive and cannot be undone.
        """
        try:
            self.store_path.write_text("", encoding="utf-8")
            logger.warning(f"Cleared event store at {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to clear event store: {e}")
            raise
