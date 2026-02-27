"""Tests for the in-memory session store."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import video_research_mcp.config as cfg_mod
from video_research_mcp.sessions import SessionStore

from google.genai import types


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


class TestSessionStore:
    def test_create_session(self):
        store = SessionStore()
        session = store.create("https://youtube.com/watch?v=abc", "general")
        assert session.session_id
        assert session.url == "https://youtube.com/watch?v=abc"
        assert session.turn_count == 0

    def test_get_session(self):
        store = SessionStore()
        session = store.create("https://youtube.com/watch?v=abc", "general")
        found = store.get(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_get_missing_session(self):
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_add_turn(self):
        store = SessionStore()
        session = store.create("https://youtube.com/watch?v=abc", "general")
        user = types.Content(role="user", parts=[types.Part(text="hello")])
        model = types.Content(role="model", parts=[types.Part(text="hi")])
        count = store.add_turn(session.session_id, user, model)
        assert count == 1
        assert len(session.history) == 2

    def test_eviction_by_max(self):
        store = SessionStore()
        store._sessions.clear()
        # Override max via config
        cfg_mod._config = cfg_mod.ServerConfig(
            gemini_api_key="test", max_sessions=2, session_timeout_hours=24
        )
        store.create("url1", "general")
        store.create("url2", "general")
        store.create("url3", "general")  # Should evict oldest
        assert store.count <= 2

    def test_expired_sessions_evicted(self):
        store = SessionStore()
        store._sessions.clear()
        cfg_mod._config = cfg_mod.ServerConfig(
            gemini_api_key="test", max_sessions=50, session_timeout_hours=1
        )
        session = store.create("url1", "general")
        # Manually expire
        session.last_active = datetime.now() - timedelta(hours=2)
        store._evict_expired()
        assert store.get(session.session_id) is None

    def test_history_trimmed_to_max_turn_window(self):
        store = SessionStore()
        cfg_mod._config = cfg_mod.ServerConfig(
            gemini_api_key="test",
            max_sessions=50,
            session_timeout_hours=24,
            session_max_turns=2,
        )
        session = store.create("https://youtube.com/watch?v=abc", "general")
        for i in range(3):
            user = types.Content(role="user", parts=[types.Part(text=f"u{i}")])
            model = types.Content(role="model", parts=[types.Part(text=f"m{i}")])
            store.add_turn(session.session_id, user, model)

        assert session.turn_count == 3
        assert len(session.history) == 4
        latest_text = [p.text for c in session.history for p in c.parts if p.text]
        assert latest_text == ["u1", "m1", "u2", "m2"]
