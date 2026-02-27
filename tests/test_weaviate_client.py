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
        # Mock collection config for _evolve_collection
        mock_col = MagicMock()
        mock_col.config.get.return_value = MagicMock(properties=[])
        mock_client.collections.get.return_value = mock_col
        mock_connect.return_value = mock_client

        WeaviateClient.get()
        mock_client.collections.create_from_dict.assert_not_called()


class TestEvolveCollection:
    """Tests for _evolve_collection()."""

    def test_adds_missing_properties(self, clean_config):
        """_evolve_collection adds properties not present in the collection."""
        import video_research_mcp.weaviate_client as mod
        from video_research_mcp.weaviate_client import WeaviateClient
        from video_research_mcp.weaviate_schema import CollectionDef, PropertyDef

        mock_client = MagicMock()
        mod._client = mock_client

        # Existing collection has only created_at
        existing_prop = MagicMock()
        existing_prop.name = "created_at"
        mock_col = MagicMock()
        mock_col.config.get.return_value = MagicMock(properties=[existing_prop])
        mock_client.collections.get.return_value = mock_col

        col_def = CollectionDef(
            name="TestCollection",
            properties=[
                PropertyDef("created_at", ["date"], "Timestamp", skip_vectorization=True),
                PropertyDef("new_field", ["text"], "A new field"),
                PropertyDef("another_field", ["int"], "Another new field", skip_vectorization=True),
            ],
        )

        WeaviateClient._evolve_collection(col_def)
        assert mock_col.config.add_property.call_count == 2

    def test_skips_existing_properties(self, clean_config):
        """_evolve_collection doesn't re-add existing properties."""
        import video_research_mcp.weaviate_client as mod
        from video_research_mcp.weaviate_client import WeaviateClient
        from video_research_mcp.weaviate_schema import CollectionDef, PropertyDef

        mock_client = MagicMock()
        mod._client = mock_client

        # All properties already exist
        prop1 = MagicMock()
        prop1.name = "field_a"
        prop2 = MagicMock()
        prop2.name = "field_b"
        mock_col = MagicMock()
        mock_col.config.get.return_value = MagicMock(properties=[prop1, prop2])
        mock_client.collections.get.return_value = mock_col

        col_def = CollectionDef(
            name="TestCollection",
            properties=[
                PropertyDef("field_a", ["text"], "Field A"),
                PropertyDef("field_b", ["int"], "Field B"),
            ],
        )

        WeaviateClient._evolve_collection(col_def)
        mock_col.config.add_property.assert_not_called()


class TestEnsureReferences:
    """Tests for _ensure_references()."""

    def test_adds_missing_references(self, clean_config):
        """_ensure_references adds cross-references from collection defs."""
        import video_research_mcp.weaviate_client as mod
        from video_research_mcp.weaviate_client import WeaviateClient
        from video_research_mcp.weaviate_schema import CollectionDef, ReferenceDef

        mock_client = MagicMock()
        mod._client = mock_client
        mock_col = MagicMock()
        mock_client.collections.get.return_value = mock_col

        collections = [
            CollectionDef(
                name="VideoAnalyses",
                references=[ReferenceDef("has_metadata", "VideoMetadata")],
            ),
            CollectionDef(name="ContentAnalyses"),  # no references
        ]

        WeaviateClient._ensure_references(collections)
        mock_col.config.add_reference.assert_called_once()

    def test_reference_failure_is_non_fatal(self, clean_config):
        """_ensure_references swallows errors from already-existing references."""
        import video_research_mcp.weaviate_client as mod
        from video_research_mcp.weaviate_client import WeaviateClient
        from video_research_mcp.weaviate_schema import CollectionDef, ReferenceDef

        mock_client = MagicMock()
        mod._client = mock_client
        mock_col = MagicMock()
        mock_col.config.add_reference.side_effect = Exception("Already exists")
        mock_client.collections.get.return_value = mock_col

        collections = [
            CollectionDef(
                name="Test",
                references=[ReferenceDef("ref", "Target")],
            ),
        ]
        # Should not raise
        WeaviateClient._ensure_references(collections)


class TestResolveDataType:
    """Tests for _resolve_data_type()."""

    def test_maps_known_types(self):
        """_resolve_data_type maps all standard type strings."""
        from weaviate.classes.config import DataType
        from video_research_mcp.weaviate_client import _resolve_data_type

        assert _resolve_data_type("text") == DataType.TEXT
        assert _resolve_data_type("text[]") == DataType.TEXT_ARRAY
        assert _resolve_data_type("int") == DataType.INT
        assert _resolve_data_type("number") == DataType.NUMBER
        assert _resolve_data_type("boolean") == DataType.BOOL
        assert _resolve_data_type("date") == DataType.DATE

    def test_raises_on_unknown_type(self):
        """_resolve_data_type raises ValueError for unknown types."""
        from video_research_mcp.weaviate_client import _resolve_data_type

        with pytest.raises(ValueError, match="Unknown data type"):
            _resolve_data_type("blob")
