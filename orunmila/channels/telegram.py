"""
Telegram Channel - Send events to Telegram bot.

Formats events as Taylor-compliant messages and sends via Telegram bot API.
"""

from typing import Optional
import logging
import requests

from ..events.contracts import EventEnvelope, Severity

logger = logging.getLogger(__name__)


class TelegramChannel:
    """
    Sends events to Telegram channel via bot.

    - Formats events as readable messages
    - Includes Taylor summary
    - Supports severity-based formatting (emojis)
    """

    # Severity emojis
    SEVERITY_EMOJI = {
        Severity.DEBUG: "🔍",
        Severity.INFO: "ℹ️",
        Severity.WARN: "⚠️",
        Severity.ERROR: "❌",
        Severity.CRITICAL: "🚨",
    }

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram channel.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info(f"TelegramChannel initialized for chat {chat_id}")

    def send_event(self, event: EventEnvelope):
        """
        Send event to Telegram.

        Args:
            event: Event to send
        """
        message = self._format_event(event)

        try:
            self._send_message(message)
            logger.info(f"Sent event {event.event_id} to Telegram")
        except Exception as e:
            logger.error(f"Failed to send event {event.event_id} to Telegram: {e}")

    def _format_event(self, event: EventEnvelope) -> str:
        """
        Format event as Telegram message.

        Args:
            event: Event to format

        Returns:
            Formatted message text
        """
        emoji = self.SEVERITY_EMOJI.get(event.severity, "")
        taylor = event.taylor_summary

        message = f"{emoji} **{event.severity.value.upper()}**: {event.event_type}\n\n"
        message += f"**Observation:**\n{taylor.observation}\n\n"
        message += f"**Implication:**\n{taylor.implication}\n\n"

        if taylor.constraints:
            message += f"**Constraints:**\n"
            for constraint in taylor.constraints:
                message += f"• {constraint}\n"
            message += "\n"

        if taylor.choice_set:
            message += f"**Actions:**\n"
            for choice in taylor.choice_set:
                message += f"• {choice}\n"
            message += "\n"

        if taylor.meta_clarifier:
            message += f"**Context:** {taylor.meta_clarifier}\n\n"

        message += f"_Event ID: {event.event_id}_\n"
        message += f"_Timestamp: {event.timestamp}_"

        return message

    def _send_message(self, text: str):
        """
        Send message via Telegram bot API.

        Args:
            text: Message text
        """
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

    def test_connection(self) -> bool:
        """
        Test Telegram connection.

        Returns:
            True if connection successful
        """
        try:
            self._send_message("🧪 Test message from Orunmila Events System")
            logger.info("Telegram connection test successful")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False


def create_telegram_handler(bot_token: str, chat_id: str):
    """
    Create Telegram handler function for EventRouter.

    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID

    Returns:
        Handler function
    """
    channel = TelegramChannel(bot_token, chat_id)

    def handler(event: EventEnvelope):
        channel.send_event(event)

    return handler
