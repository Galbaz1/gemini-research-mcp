"""In-memory session store for multi-turn video exploration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from google.genai import types

from .config import get_config


@dataclass
class VideoSession:
    """Persistent conversation context for a single video."""

    session_id: str
    url: str
    mode: str
    video_title: str = ""
    history: list[types.Content] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    turn_count: int = 0


class SessionStore:
    """Process-wide session registry with TTL eviction."""

    def __init__(self) -> None:
        self._sessions: dict[str, VideoSession] = {}

    def create(self, url: str, mode: str, video_title: str = "") -> VideoSession:
        """Create a new session, evicting expired ones first."""
        self._evict_expired()
        cfg = get_config()
        if len(self._sessions) >= cfg.max_sessions:
            oldest_id = min(self._sessions, key=lambda k: self._sessions[k].last_active)
            del self._sessions[oldest_id]

        sid = uuid.uuid4().hex[:12]
        session = VideoSession(
            session_id=sid,
            url=url,
            mode=mode,
            video_title=video_title,
        )
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> VideoSession | None:
        self._evict_expired()
        return self._sessions.get(session_id)

    def add_turn(
        self,
        session_id: str,
        user_content: types.Content,
        model_content: types.Content,
    ) -> int:
        """Append a user+model turn pair. Returns new turn count."""
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session {session_id} not found")
        session.history.append(user_content)
        session.history.append(model_content)
        session.turn_count += 1
        session.last_active = datetime.now()
        return session.turn_count

    def _evict_expired(self) -> int:
        timeout = timedelta(hours=get_config().session_timeout_hours)
        now = datetime.now()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_active > timeout]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    @property
    def count(self) -> int:
        return len(self._sessions)


# Module-level singleton
session_store = SessionStore()
