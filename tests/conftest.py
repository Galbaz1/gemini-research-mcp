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


@pytest.fixture()
def mock_weaviate_client():
    """Patch WeaviateClient for unit tests — provides mock client + collection."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.get.return_value = mock_collection
    mock_client.collections.list_all.return_value = {}
    mock_client.is_ready.return_value = True

    # Mock data operations
    mock_collection.data.insert.return_value = "test-uuid-1234"
    mock_collection.data.update.return_value = None
    mock_collection.query.hybrid.return_value = MagicMock(objects=[])
    mock_collection.query.near_object.return_value = MagicMock(objects=[])
    mock_collection.query.fetch_objects.return_value = MagicMock(objects=[])
    mock_collection.aggregate.over_all.return_value = MagicMock(total_count=0)

    with (
        patch("video_research_mcp.weaviate_client._client", mock_client),
        patch("video_research_mcp.weaviate_client._schema_ensured", True),
        patch("video_research_mcp.weaviate_client.WeaviateClient.get", return_value=mock_client),
        patch("video_research_mcp.weaviate_client.WeaviateClient.is_available", return_value=True),
    ):
        yield {
            "client": mock_client,
            "collection": mock_collection,
        }


@pytest.fixture()
def mock_weaviate_disabled(monkeypatch, clean_config):
    """Ensure Weaviate is disabled — empty WEAVIATE_URL."""
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    monkeypatch.delenv("WEAVIATE_API_KEY", raising=False)
