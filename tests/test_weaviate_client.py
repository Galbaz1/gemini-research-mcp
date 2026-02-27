"""Tests for WeaviateClient singleton."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWeaviateClientGet:
    """Tests for WeaviateClient.get()."""

    def test_raises_when_url_not_configured(self, clean_config, monkeypatch):
        """get() raises ValueError when WEAVIATE_URL is empty."""
        monkeypatch.delenv("WEAVIATE_URL", raising=False)
        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()
        with pytest.raises(ValueError, match="WEAVIATE_URL not configured"):
            WeaviateClient.get()

    @patch("video_research_mcp.weaviate_client.weaviate.connect_to_weaviate_cloud")
    def test_creates_client_when_configured(self, mock_connect, clean_config, monkeypatch):
        """get() creates and returns a client when WEAVIATE_URL is set."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test-cluster.weaviate.network")
        monkeypatch.setenv("WEAVIATE_API_KEY", "test-key")
        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()

        mock_client = MagicMock()
        mock_client.collections.list_all.return_value = {}
        mock_connect.return_value = mock_client

        result = WeaviateClient.get()
        assert result is mock_client
        mock_connect.assert_called_once()

    @patch("video_research_mcp.weaviate_client.weaviate.connect_to_weaviate_cloud")
    def test_returns_same_client_on_subsequent_calls(self, mock_connect, clean_config, monkeypatch):
        """get() returns the cached singleton on second call."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()

        mock_client = MagicMock()
        mock_client.collections.list_all.return_value = {}
        mock_connect.return_value = mock_client

        first = WeaviateClient.get()
        second = WeaviateClient.get()
        assert first is second
        assert mock_connect.call_count == 1


class TestWeaviateClientClose:
    """Tests for close() and reset()."""

    def test_close_clears_singleton(self, clean_config):
        """close() sets internal state to None."""
        import video_research_mcp.weaviate_client as mod
        mod._client = MagicMock()
        mod._schema_ensured = True

        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.close()

        assert mod._client is None
        assert mod._schema_ensured is False

    def test_reset_clears_singleton(self, clean_config):
        """reset() clears state without calling close on the client."""
        import video_research_mcp.weaviate_client as mod
        mod._client = MagicMock()
        mod._schema_ensured = True

        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()

        assert mod._client is None
        assert mod._schema_ensured is False


class TestWeaviateClientIsAvailable:
    """Tests for is_available()."""

    def test_false_when_not_configured(self, clean_config, monkeypatch):
        """is_available() returns False when weaviate_enabled is False."""
        monkeypatch.delenv("WEAVIATE_URL", raising=False)
        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()
        assert WeaviateClient.is_available() is False

    def test_true_when_configured_and_ready(self, mock_weaviate_client):
        """is_available() returns True when client is ready."""
        from video_research_mcp.weaviate_client import WeaviateClient
        assert WeaviateClient.is_available() is True


class TestEnsureCollections:
    """Tests for ensure_collections()."""

    @patch("video_research_mcp.weaviate_client.weaviate.connect_to_weaviate_cloud")
    def test_skips_existing_collections(self, mock_connect, clean_config, monkeypatch):
        """ensure_collections() does not recreate existing collections."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_client import WeaviateClient
        WeaviateClient.reset()

        mock_client = MagicMock()
        # Simulate all collections already existing
        existing = {
            name: MagicMock(name=name) for name in [
                "ResearchFindings", "VideoAnalyses", "ContentAnalyses",
                "VideoMetadata", "SessionTranscripts", "WebSearchResults", "ResearchPlans",
            ]
        }
        mock_client.collections.list_all.return_value = existing
        mock_connect.return_value = mock_client

        WeaviateClient.get()
        mock_client.collections.create_from_dict.assert_not_called()
