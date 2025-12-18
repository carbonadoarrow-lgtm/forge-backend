"""
Event Channels - Delivery mechanisms for events.

Provides integrations with external services (Telegram, email, etc.).
"""

__version__ = "0.1.0"

from .telegram import TelegramChannel

__all__ = [
    "TelegramChannel",
]
