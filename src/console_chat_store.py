"""
Console Chat Store - Single source of truth for operator chat sessions.

This is separate from mission/context-specific chat - it's dedicated for
operators to interact with Forge OS for general queries, troubleshooting,
and advisory conversations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock
from typing import Dict, List, Literal, Any, Optional
from pydantic import BaseModel


ChatRole = Literal["user", "assistant", "system"]


class ConsoleChatMessage(BaseModel):
    """A single message in a console chat session."""
    id: str
    session_id: str
    role: ChatRole
    content: str
    created_at: str
    meta: Dict[str, Any] = {}


class ConsoleChatSession(BaseModel):
    """An operator chat session with Forge OS."""
    id: str
    title: str
    sphere: str  # "forge" | "orunmila"
    created_at: str
    updated_at: str
    last_message_preview: str
    unread_count: int
    context: Dict[str, Any] = {}


class ConsoleChatStore:
    """
    Thread-safe in-memory store for console chat sessions and messages.

    This is the operator's main interface to Forge OS - for asking questions,
    getting advice, troubleshooting issues, etc.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, ConsoleChatSession] = {}
        self._messages: Dict[str, List[ConsoleChatMessage]] = {}
        self._lock = Lock()

    def _now(self) -> str:
        """Generate ISO-8601 UTC timestamp."""
        return datetime.utcnow().isoformat() + "Z"

    def list_sessions(self) -> List[ConsoleChatSession]:
        """
        Return all chat sessions, sorted by most recently updated first.
        """
        with self._lock:
            return sorted(
                self._sessions.values(),
                key=lambda s: s.updated_at,
                reverse=True,
            )

    def get_session(self, session_id: str) -> Optional[ConsoleChatSession]:
        """Get a specific session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def create_session(
        self,
        title: str | None = None,
        sphere: str = "forge",
        context: Dict[str, Any] | None = None,
    ) -> ConsoleChatSession:
        """
        Create a new chat session.

        Args:
            title: Session title (defaults to "New session")
            sphere: "forge" or "orunmila"
            context: Optional context dict (e.g., related mission, run, etc.)
        """
        session_id = f"cs_{uuid.uuid4().hex[:10]}"
        now = self._now()

        session = ConsoleChatSession(
            id=session_id,
            title=title or "New session",
            sphere=sphere,
            created_at=now,
            updated_at=now,
            last_message_preview="",
            unread_count=0,
            context=context or {},
        )

        with self._lock:
            self._sessions[session_id] = session
            self._messages[session_id] = []

        return session

    def list_messages(self, session_id: str) -> List[ConsoleChatMessage]:
        """
        Return all messages for a session, in chronological order.
        """
        with self._lock:
            return self._messages.get(session_id, [])

    def add_message(
        self,
        session_id: str,
        role: ChatRole,
        content: str,
        meta: Dict[str, Any] | None = None,
    ) -> ConsoleChatMessage:
        """
        Add a message to a session.

        This also updates the session's updated_at, last_message_preview,
        and unread_count (if role is "assistant").
        """
        now = self._now()

        msg = ConsoleChatMessage(
            id=f"cm_{uuid.uuid4().hex[:10]}",
            session_id=session_id,
            role=role,
            content=content,
            created_at=now,
            meta=meta or {},
        )

        with self._lock:
            # Add message
            self._messages.setdefault(session_id, []).append(msg)

            # Update session metadata
            session = self._sessions.get(session_id)
            if session:
                session.updated_at = now
                session.last_message_preview = content[:200]

                # Increment unread count for assistant messages
                if role == "assistant":
                    session.unread_count += 1

                self._sessions[session_id] = session

        return msg

    def mark_read(self, session_id: str) -> None:
        """
        Mark all messages in a session as read (reset unread_count to 0).
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.unread_count = 0
                self._sessions[session_id] = session


# Global singleton
console_chat_store = ConsoleChatStore()
