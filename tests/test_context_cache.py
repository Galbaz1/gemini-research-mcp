"""Tests for the Gemini context cache registry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from google.genai import types

import video_research_mcp.config as cfg_mod
import video_research_mcp.context_cache as cc_mod


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Ensure cache registry is empty and _loaded reset between tests."""
    cc_mod._registry.clear()
    cc_mod._loaded = True  # Prevent disk load during unit tests
    yield
    cc_mod._registry.clear()
    cc_mod._loaded = True


@pytest.fixture(autouse=True)
def _isolate_registry_path(tmp_path):
    """Redirect registry persistence to temp dir — never touch real filesystem."""
    json_path = tmp_path / "context_cache_registry.json"
    with patch.object(cc_mod, "_registry_path", return_value=json_path):
        yield json_path


def _video_parts() -> list[types.Part]:
    return [types.Part(file_data=types.FileData(file_uri="https://www.youtube.com/watch?v=abc"))]


class TestGetOrCreate:
    async def test_creates_cache_on_first_call(self):
        """GIVEN no existing cache WHEN get_or_create called THEN creates one."""
        mock_cached = MagicMock()
        mock_cached.name = "cachedContents/xyz123"

        mock_client = MagicMock()
        mock_client.aio.caches.create = AsyncMock(return_value=mock_cached)

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.get_or_create("abc", _video_parts(), "gemini-pro")

        assert result == "cachedContents/xyz123"
        assert cc_mod._registry[("abc", "gemini-pro")] == "cachedContents/xyz123"

    async def test_returns_cached_on_second_call(self):
        """GIVEN a registry entry WHEN get_or_create called THEN validates and returns it."""
        cc_mod._registry[("abc", "gemini-pro")] = "cachedContents/existing"

        mock_cached = MagicMock()
        mock_cached.name = "cachedContents/existing"

        mock_client = MagicMock()
        mock_client.aio.caches.get = AsyncMock(return_value=mock_cached)

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.get_or_create("abc", _video_parts(), "gemini-pro")

        assert result == "cachedContents/existing"
        mock_client.aio.caches.create.assert_not_called()

    async def test_recreates_on_stale_cache(self):
        """GIVEN a stale registry entry WHEN validated THEN recreates cache."""
        cc_mod._registry[("abc", "gemini-pro")] = "cachedContents/stale"

        mock_new = MagicMock()
        mock_new.name = "cachedContents/new123"

        mock_client = MagicMock()
        mock_client.aio.caches.get = AsyncMock(side_effect=Exception("NOT_FOUND"))
        mock_client.aio.caches.create = AsyncMock(return_value=mock_new)

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.get_or_create("abc", _video_parts(), "gemini-pro")

        assert result == "cachedContents/new123"

    async def test_returns_none_on_create_failure(self):
        """GIVEN no registry entry WHEN create fails THEN returns None."""
        mock_client = MagicMock()
        mock_client.aio.caches.create = AsyncMock(side_effect=Exception("API error"))

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.get_or_create("abc", _video_parts(), "gemini-pro")

        assert result is None
        assert ("abc", "gemini-pro") not in cc_mod._registry


class TestRefreshTtl:
    async def test_refresh_success(self):
        """GIVEN an active cache WHEN refresh_ttl called THEN returns True."""
        mock_client = MagicMock()
        mock_client.aio.caches.update = AsyncMock()

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.refresh_ttl("cachedContents/xyz")

        assert result is True
        mock_client.aio.caches.update.assert_called_once()

    async def test_refresh_failure(self):
        """GIVEN an expired cache WHEN refresh_ttl called THEN returns False."""
        mock_client = MagicMock()
        mock_client.aio.caches.update = AsyncMock(side_effect=Exception("NOT_FOUND"))

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            result = await cc_mod.refresh_ttl("cachedContents/expired")

        assert result is False


class TestLookup:
    def test_lookup_hit(self):
        """GIVEN a registry entry WHEN lookup called THEN returns name."""
        cc_mod._registry[("vid1", "model1")] = "cachedContents/abc"
        assert cc_mod.lookup("vid1", "model1") == "cachedContents/abc"

    def test_lookup_miss(self):
        """GIVEN no registry entry WHEN lookup called THEN returns None."""
        assert cc_mod.lookup("unknown", "model1") is None


class TestClear:
    async def test_clear_empty_registry_without_api_key(self, monkeypatch):
        """GIVEN empty registry and no key WHEN clear called THEN no client lookup."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with patch("video_research_mcp.context_cache.GeminiClient.get") as mock_get:
            count = await cc_mod.clear()

        assert count == 0
        assert len(cc_mod._registry) == 0
        mock_get.assert_not_called()

    async def test_clear_client_init_failure_clears_registry(self):
        """GIVEN registry entries and no client WHEN clear called THEN registry is cleared."""
        cc_mod._registry[("a", "m")] = "cachedContents/1"

        with patch(
            "video_research_mcp.context_cache.GeminiClient.get",
            side_effect=ValueError("No Gemini API key"),
        ):
            count = await cc_mod.clear()

        assert count == 0
        assert len(cc_mod._registry) == 0

    async def test_clear_deletes_all(self):
        """GIVEN multiple registry entries WHEN clear called THEN all deleted."""
        cc_mod._registry[("a", "m")] = "cachedContents/1"
        cc_mod._registry[("b", "m")] = "cachedContents/2"

        mock_client = MagicMock()
        mock_client.aio.caches.delete = AsyncMock()

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            count = await cc_mod.clear()

        assert count == 2
        assert len(cc_mod._registry) == 0

    async def test_clear_tolerates_delete_failures(self):
        """GIVEN registry entries WHEN delete fails THEN registry still cleared."""
        cc_mod._registry[("a", "m")] = "cachedContents/1"

        mock_client = MagicMock()
        mock_client.aio.caches.delete = AsyncMock(side_effect=Exception("fail"))

        with patch("video_research_mcp.context_cache.GeminiClient.get", return_value=mock_client):
            count = await cc_mod.clear()

        assert count == 0
        assert len(cc_mod._registry) == 0


class TestSessionCacheFields:
    """Verify cache_name and model fields persist through session store + DB."""

    def test_session_create_with_cache_fields(self):
        """GIVEN cache_name and model WHEN session created THEN fields stored."""
        from video_research_mcp.sessions import SessionStore

        store = SessionStore()
        session = store.create(
            "https://youtube.com/watch?v=abc", "general",
            video_title="Test",
            cache_name="cachedContents/xyz",
            model="gemini-pro",
        )
        assert session.cache_name == "cachedContents/xyz"
        assert session.model == "gemini-pro"

    def test_session_cache_fields_default_empty(self):
        """GIVEN no cache args WHEN session created THEN fields are empty strings."""
        from video_research_mcp.sessions import SessionStore

        store = SessionStore()
        session = store.create("https://youtube.com/watch?v=abc", "general")
        assert session.cache_name == ""
        assert session.model == ""

    def test_persistence_roundtrip_with_cache_fields(self, tmp_path):
        """GIVEN cache fields WHEN persisted to SQLite THEN recoverable."""
        from video_research_mcp.sessions import SessionStore

        db_path = str(tmp_path / "sessions.db")
        store = SessionStore(db_path=db_path)
        session = store.create(
            "https://youtube.com/watch?v=abc", "general",
            video_title="Test",
            cache_name="cachedContents/persist-test",
            model="gemini-3.1-pro-preview",
        )

        store2 = SessionStore(db_path=db_path)
        recovered = store2.get(session.session_id)
        assert recovered is not None
        assert recovered.cache_name == "cachedContents/persist-test"
        assert recovered.model == "gemini-3.1-pro-preview"

    def test_migration_adds_columns(self, tmp_path):
        """GIVEN a DB without cache columns WHEN SessionDB opened THEN migrates."""
        import sqlite3

        db_path = str(tmp_path / "old.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                mode TEXT NOT NULL,
                video_title TEXT NOT NULL DEFAULT '',
                history TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                turn_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            INSERT INTO sessions VALUES (
                'old1', 'url', 'general', 'Title', '[]',
                '2025-01-01T00:00:00', '2025-01-01T00:00:00', 0
            )
        """)
        conn.commit()
        conn.close()

        from video_research_mcp.persistence import SessionDB

        db = SessionDB(db_path)
        loaded = db.load_sync("old1")
        assert loaded is not None
        assert loaded.cache_name == ""
        assert loaded.model == ""
        db.close()


class TestRegistryPersistence:
    """Verify registry save/load roundtrip and GC behavior."""

    def test_save_and_load_roundtrip(self, _isolate_registry_path):
        """GIVEN populated registry WHEN saved and reloaded THEN entries restored."""
        cc_mod._registry[("vid1", "model-a")] = "cachedContents/aaa"
        cc_mod._registry[("vid2", "model-b")] = "cachedContents/bbb"
        cc_mod._save_registry()

        cc_mod._registry.clear()
        cc_mod._loaded = False
        cc_mod._load_registry()

        assert cc_mod._registry[("vid1", "model-a")] == "cachedContents/aaa"
        assert cc_mod._registry[("vid2", "model-b")] == "cachedContents/bbb"

    def test_load_missing_file(self):
        """GIVEN no file on disk WHEN load called THEN empty registry, no error."""
        cc_mod._loaded = False
        cc_mod._load_registry()
        assert len(cc_mod._registry) == 0

    def test_load_corrupted_file(self, _isolate_registry_path):
        """GIVEN invalid JSON WHEN load called THEN falls back to empty."""
        _isolate_registry_path.write_text("not valid json {{{")
        cc_mod._loaded = False
        cc_mod._load_registry()
        assert len(cc_mod._registry) == 0

    def test_gc_caps_at_max_entries(self, _isolate_registry_path):
        """GIVEN 250 entries WHEN saved THEN capped at _MAX_REGISTRY_ENTRIES."""
        for i in range(250):
            cc_mod._registry[(f"vid{i}", "model")] = f"cachedContents/{i}"
        cc_mod._save_registry()

        assert len(cc_mod._registry) <= cc_mod._MAX_REGISTRY_ENTRIES

        cc_mod._registry.clear()
        cc_mod._loaded = False
        cc_mod._load_registry()
        assert len(cc_mod._registry) == cc_mod._MAX_REGISTRY_ENTRIES
