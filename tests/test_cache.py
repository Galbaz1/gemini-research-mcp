"""Tests for the generic file-based cache."""

from __future__ import annotations


import pytest

import video_research_mcp.config as cfg_mod
from video_research_mcp import cache


@pytest.fixture(autouse=True)
def _tmp_cache(tmp_path, monkeypatch):
    """Point cache at a temp directory."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_mod._config = None
    monkeypatch.setenv("GEMINI_CACHE_DIR", str(tmp_path / "cache"))
    cfg_mod._config = None
    yield
    cfg_mod._config = None


class TestCache:
    def test_save_and_load(self):
        data = {"title": "Test Video", "summary": "A summary"}
        assert cache.save("vid123", "analyze", "gemini-pro", data) is True

        loaded = cache.load("vid123", "analyze", "gemini-pro")
        assert loaded is not None
        assert loaded["title"] == "Test Video"

    def test_cache_miss(self):
        assert cache.load("nonexistent", "analyze", "gemini-pro") is None

    def test_clear_specific(self):
        cache.save("vid1", "analyze", "model", {"a": 1})
        cache.save("vid2", "analyze", "model", {"b": 2})
        removed = cache.clear("vid1")
        assert removed >= 1
        assert cache.load("vid1", "analyze", "model") is None
        assert cache.load("vid2", "analyze", "model") is not None

    def test_clear_specific_does_not_delete_prefix_matches(self):
        cache.save("vid1", "analyze", "model", {"a": 1})
        cache.save("vid12", "analyze", "model", {"b": 2})
        removed = cache.clear("vid1")
        assert removed == 1
        assert cache.load("vid1", "analyze", "model") is None
        assert cache.load("vid12", "analyze", "model") is not None

    def test_clear_all(self):
        cache.save("vid1", "analyze", "model", {"a": 1})
        cache.save("vid2", "analyze", "model", {"b": 2})
        removed = cache.clear()
        assert removed >= 2

    def test_stats(self):
        cache.save("vid1", "t", "m", {"x": 1})
        s = cache.stats()
        assert s["total_files"] >= 1
        assert "total_size_mb" in s

    def test_list_entries(self):
        cache.save("vid1", "t", "m", {"x": 1})
        entries = cache.list_entries()
        assert len(entries) >= 1
        assert entries[0]["content_id"] == "vid1"


class TestCacheWithInstruction:
    """Verify that instruction param differentiates cache entries."""

    def test_different_instructions_different_keys(self):
        """Same content + different instruction → different cache entries."""
        cache.save("vid1", "analyze", "model", {"a": 1}, instruction="summarize")
        cache.save("vid1", "analyze", "model", {"b": 2}, instruction="list recipes")

        loaded1 = cache.load("vid1", "analyze", "model", instruction="summarize")
        loaded2 = cache.load("vid1", "analyze", "model", instruction="list recipes")

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1["a"] == 1
        assert loaded2["b"] == 2

    def test_empty_instruction_uses_default_key(self):
        """No instruction → 'default' hash segment."""
        key_no_instr = cache.cache_key("vid1", "analyze", "model")
        key_empty = cache.cache_key("vid1", "analyze", "model", instruction="")
        assert key_no_instr == key_empty
        assert "_default_" in key_no_instr

    def test_instruction_miss(self):
        """Cache with one instruction misses for a different instruction."""
        cache.save("vid1", "analyze", "model", {"a": 1}, instruction="summarize")
        assert cache.load("vid1", "analyze", "model", instruction="different") is None

    def test_clear_clears_all_instructions(self):
        """Clearing by content_id removes all instruction variants."""
        cache.save("vid1", "analyze", "model", {"a": 1}, instruction="summarize")
        cache.save("vid1", "analyze", "model", {"b": 2}, instruction="list recipes")
        removed = cache.clear("vid1")
        assert removed == 2
