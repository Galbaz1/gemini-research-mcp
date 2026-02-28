"""Tests for new Weaviate store functions (community, concepts, calls)."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestNewStoreGuards:
    """Test that new store functions respect the enabled guard."""

    async def test_store_community_noop_when_disabled(self, mock_weaviate_disabled):
        """store_community_reaction returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_community_reaction
        result = await store_community_reaction({"video_id": "abc"})
        assert result is None

    async def test_store_concept_noop_when_disabled(self, mock_weaviate_disabled):
        """store_concept_knowledge returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_concept_knowledge
        result = await store_concept_knowledge({"concept_name": "test"})
        assert result is None

    async def test_store_edges_noop_when_disabled(self, mock_weaviate_disabled):
        """store_relationship_edges returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_relationship_edges
        result = await store_relationship_edges([{"from_concept": "A", "to_concept": "B"}])
        assert result is None

    async def test_store_calls_noop_when_disabled(self, mock_weaviate_disabled):
        """store_call_notes returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_call_notes
        result = await store_call_notes({"title": "Standup"})
        assert result is None


class TestNewStoreWhenEnabled:
    """Test that new store functions write to Weaviate when enabled."""

    async def test_store_community_dedup_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_community_reaction uses deterministic UUID and adds cross-ref on replace path."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_community_reaction
        result = await store_community_reaction({
            "video_id": "abc123",
            "video_title": "Test Video",
            "comment_count": 100,
            "sentiment_positive": 65.0,
            "sentiment_negative": 15.0,
            "sentiment_neutral": 20.0,
            "themes_positive": ["great content"],
            "themes_critical": ["too long"],
            "consensus": "Mostly positive",
            "notable_opinions": [{"author": "user1", "quote": "amazing"}],
        })
        assert result is not None
        # Should try replace first (deterministic UUID pattern)
        mock_weaviate_client["collection"].data.replace.assert_called_once()
        # Cross-ref to VideoMetadata must run on BOTH replace and insert paths
        mock_weaviate_client["collection"].data.reference_add.assert_called_once()

    async def test_store_concept_dedup_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_concept_knowledge uses deterministic UUID from source_url + concept_name."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_concept_knowledge
        result = await store_concept_knowledge({
            "concept_name": "Jevons Paradox",
            "state": "fuzzy",
            "source_url": "https://youtube.com/watch?v=abc",
            "source_title": "Economics Talk",
            "source_category": "video",
            "description": "Efficiency gains increase consumption",
            "timestamp": "30:26",
        })
        assert result is not None
        mock_weaviate_client["collection"].data.replace.assert_called_once()

    async def test_store_edges_batch_insert(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_relationship_edges uses insert_many for batch import."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")

        mock_obj1 = MagicMock()
        mock_obj1.uuid = "edge-uuid-1"
        mock_obj2 = MagicMock()
        mock_obj2.uuid = "edge-uuid-2"
        mock_result = MagicMock()
        mock_result.all_objects = [mock_obj1, mock_obj2]
        mock_weaviate_client["collection"].data.insert_many.return_value = mock_result

        from video_research_mcp.weaviate_store import store_relationship_edges
        result = await store_relationship_edges([
            {"from_concept": "A", "to_concept": "B", "relationship_type": "enables"},
            {"from_concept": "B", "to_concept": "C", "relationship_type": "example_of"},
        ])
        assert result is not None
        assert len(result) == 2
        mock_weaviate_client["collection"].data.insert_many.assert_called_once()

    async def test_store_edges_disabled_returns_none(self, mock_weaviate_disabled):
        """store_relationship_edges returns None when disabled."""
        from video_research_mcp.weaviate_store import store_relationship_edges
        result = await store_relationship_edges([])
        assert result is None

    async def test_store_edges_empty_returns_empty(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_relationship_edges returns [] for empty input when enabled."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_relationship_edges
        result = await store_relationship_edges([])
        assert result == []

    async def test_store_calls_returns_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_call_notes returns UUID string when successful."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_call_notes
        result = await store_call_notes({
            "video_id": "vid1",
            "source_url": "https://youtube.com/watch?v=vid1",
            "title": "Weekly Standup",
            "summary": "Sprint review and planning",
            "participants": ["Alice", "Bob"],
            "decisions": ["Ship v2 next week"],
            "action_items": ["Alice: update docs"],
            "topics_discussed": ["Sprint review", "Planning"],
        })
        assert result == "test-uuid-1234"
        mock_weaviate_client["collection"].data.insert.assert_called_once()


class TestNewStoreErrorHandling:
    """Test that new store functions handle errors gracefully."""

    async def test_store_community_returns_none_on_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_community_reaction returns None (not raises) on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.replace.side_effect = RuntimeError("fail")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("fail")

        from video_research_mcp.weaviate_store import store_community_reaction
        result = await store_community_reaction({"video_id": "abc"})
        assert result is None

    async def test_store_concept_returns_none_on_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_concept_knowledge returns None (not raises) on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.replace.side_effect = RuntimeError("fail")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("fail")

        from video_research_mcp.weaviate_store import store_concept_knowledge
        result = await store_concept_knowledge({"concept_name": "test", "source_url": "http://x"})
        assert result is None

    async def test_store_edges_returns_none_on_batch_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_relationship_edges returns None when insert_many fails."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert_many.side_effect = RuntimeError("fail")

        from video_research_mcp.weaviate_store import store_relationship_edges
        result = await store_relationship_edges([{"from_concept": "A", "to_concept": "B"}])
        assert result is None

    async def test_store_calls_returns_none_on_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_call_notes returns None (not raises) on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("fail")

        from video_research_mcp.weaviate_store import store_call_notes
        result = await store_call_notes({"title": "Standup"})
        assert result is None


class TestVideoDedupUUID:
    """Test deterministic UUID in store_video_analysis."""

    async def test_store_video_uses_deterministic_uuid(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_video_analysis uses deterministic UUID when content_id is present."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_video_analysis
        result = await store_video_analysis(
            {"title": "Test", "summary": "A test"},
            "vid123", "summarize", "https://youtube.com/watch?v=vid123",
        )
        assert result is not None
        # Should try replace first (deterministic UUID pattern)
        mock_weaviate_client["collection"].data.replace.assert_called_once()
