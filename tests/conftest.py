"""Shared test fixtures for gemini-research-mcp."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_dummy_api_key(monkeypatch):
    """Ensure tests never hit real Gemini API."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


@pytest.fixture()
def mock_gemini_client():
    """Patch GeminiClient.get() and .generate() for unit tests."""
    with (
        patch("gemini_research_mcp.client.GeminiClient.get") as mock_get,
        patch(
            "gemini_research_mcp.client.GeminiClient.generate", new_callable=AsyncMock
        ) as mock_gen,
    ):
        client = MagicMock()
        mock_get.return_value = client
        yield {"get": mock_get, "generate": mock_gen, "client": client}


@pytest.fixture()
def clean_config():
    """Reset the config singleton between tests."""
    import gemini_research_mcp.config as cfg_mod

    cfg_mod._config = None
    yield
    cfg_mod._config = None
