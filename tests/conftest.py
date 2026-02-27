"""Shared test fixtures for video-research-mcp."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_dummy_api_key(monkeypatch):
    """Ensure tests never hit real Gemini API."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


@pytest.fixture()
def mock_gemini_client():
    """Patch GeminiClient.get(), .generate(), and .generate_structured() for unit tests."""
    with (
        patch("video_research_mcp.client.GeminiClient.get") as mock_get,
        patch(
            "video_research_mcp.client.GeminiClient.generate", new_callable=AsyncMock
        ) as mock_gen,
        patch(
            "video_research_mcp.client.GeminiClient.generate_structured",
            new_callable=AsyncMock,
        ) as mock_structured,
    ):
        client = MagicMock()
        mock_get.return_value = client
        yield {
            "get": mock_get,
            "generate": mock_gen,
            "generate_structured": mock_structured,
            "client": client,
        }


@pytest.fixture()
def clean_config():
    """Reset the config singleton between tests."""
    import video_research_mcp.config as cfg_mod

    cfg_mod._config = None
    yield
    cfg_mod._config = None
