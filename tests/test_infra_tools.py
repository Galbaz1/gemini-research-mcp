"""Tests for infrastructure tools."""

from __future__ import annotations

import pytest

import video_research_mcp.config as cfg_mod
from video_research_mcp.tools.infra import infra_cache, infra_configure


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


class TestInfraTools:
    @pytest.mark.asyncio
    async def test_infra_configure_updates_runtime_config(self):
        out = await infra_configure(model="gemini-test", thinking_level="low", temperature=0.7)
        cfg = out["current_config"]
        assert cfg["default_model"] == "gemini-test"
        assert cfg["default_thinking_level"] == "low"
        assert cfg["default_temperature"] == 0.7
        assert "gemini_api_key" not in cfg

    @pytest.mark.asyncio
    async def test_infra_configure_invalid_thinking_level_returns_error(self):
        out = await infra_configure(thinking_level="ultra")
        assert out["category"] == "API_INVALID_ARGUMENT"
        assert out["retryable"] is False

    @pytest.mark.asyncio
    async def test_infra_cache_unknown_action(self):
        out = await infra_cache(action="wat")
        assert "Unknown action" in out["error"]
