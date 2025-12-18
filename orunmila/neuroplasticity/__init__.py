"""
Neuroplasticity - Episode logging and automatic intent application.

Tracks interaction episodes and distills clear intents for auto-application to config.
"""

__version__ = "0.1.0"

from .contracts import Episode, Intent
from .logger import EpisodeLogger
from .distiller import IntentDistiller
from .applicator import IntentApplicator

__all__ = [
    "Episode",
    "Intent",
    "EpisodeLogger",
    "IntentDistiller",
    "IntentApplicator",
]
