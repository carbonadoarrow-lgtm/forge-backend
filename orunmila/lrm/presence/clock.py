"""
Business Hours Clock - Calculate elapsed time excluding weekends.

Provides timezone-aware business hours calculation for presence tracking.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BusinessHoursClock:
    """
    Calculate business hours elapsed between timestamps.

    - Excludes weekends (Saturday=5, Sunday=6)
    - Timezone-aware (defaults to UTC)
    - Used for presence state transitions
    """

    def __init__(self, timezone: str = "UTC"):
        """
        Initialize business hours clock.

        Args:
            timezone: Timezone name (e.g., "UTC", "America/New_York")
        """
        self.timezone = timezone
        logger.debug(f"BusinessHoursClock initialized with timezone: {timezone}")

    def calculate_business_hours(
        self,
        start_timestamp: str,
        end_timestamp: Optional[str] = None,
    ) -> float:
        """
        Calculate business hours between two timestamps.

        Excludes weekends (Saturday, Sunday).

        Args:
            start_timestamp: Start time (ISO 8601)
            end_timestamp: End time (ISO 8601), defaults to now

        Returns:
            Business hours elapsed (float)
        """
        start = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_timestamp.replace("Z", "+00:00")) if end_timestamp else datetime.utcnow()

        total_hours = 0.0
        current = start

        # Iterate hour by hour, skip weekends
        while current < end:
            # Check if current hour is on a weekend
            if current.weekday() < 5:  # Monday=0, Friday=4
                # Add 1 hour
                next_hour = current + timedelta(hours=1)
                if next_hour <= end:
                    total_hours += 1.0
                else:
                    # Partial hour
                    remaining_seconds = (end - current).total_seconds()
                    total_hours += remaining_seconds / 3600.0
                    break
                current = next_hour
            else:
                # Skip to Monday 00:00
                days_until_monday = (7 - current.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 1  # If Sunday, skip to Monday
                current = (current + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)

        return total_hours

    def is_weekend(self, timestamp: str) -> bool:
        """
        Check if timestamp falls on a weekend.

        Args:
            timestamp: ISO 8601 timestamp

        Returns:
            True if Saturday or Sunday
        """
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.weekday() >= 5  # Saturday=5, Sunday=6

    def next_business_hour(self, timestamp: str) -> str:
        """
        Get next business hour from timestamp.

        If timestamp is on weekend, returns Monday 00:00.

        Args:
            timestamp: ISO 8601 timestamp

        Returns:
            Next business hour (ISO 8601)
        """
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        if dt.weekday() >= 5:  # Weekend
            # Skip to Monday 00:00
            days_until_monday = (7 - dt.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 1
            next_dt = (dt + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Just add 1 hour
            next_dt = dt + timedelta(hours=1)

        return next_dt.isoformat()
