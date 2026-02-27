"""Tests for knowledge query tools."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestKnowledgeSearch:
    """Tests for knowledge_search tool."""

    async def test_returns_empty_when_disabled(self, mock_weaviate_disabled):
        """knowledge_search returns empty result when Weaviate not configured."""
        from video_research_mcp.tools.knowledge import knowledge_search
        result = await knowledge_search(query="AI research")
        assert result["query"] == "AI research"
        assert result["total_results"] == 0

    async def test_returns_search_result_structure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_search returns KnowledgeSearchResult dict."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.tools.knowledge import knowledge_search
        result = await knowledge_search(query="AI research")
        assert "query" in result
        assert "total_results" in result
        assert "results" in result
        assert result["query"] == "AI research"

    async def test_searches_all_collections_by_default(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_search queries all 7 collections when none specified."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.tools.knowledge import knowledge_search
        await knowledge_search(query="test")
        assert mock_weaviate_client["client"].collections.get.call_count == 7

    async def test_respects_collection_filter(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_search only queries specified collections."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.tools.knowledge import knowledge_search
        await knowledge_search(query="test", collections=["VideoAnalyses", "VideoMetadata"])
        assert mock_weaviate_client["client"].collections.get.call_count == 2

    async def test_returns_ranked_results(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_search returns results sorted by score descending."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        obj1 = MagicMock()
        obj1.uuid = "uuid-1"
        obj1.properties = {"title": "First"}
        obj1.metadata = MagicMock(score=0.9)

        obj2 = MagicMock()
        obj2.uuid = "uuid-2"
        obj2.properties = {"title": "Second"}
        obj2.metadata = MagicMock(score=0.5)

        mock_collection = MagicMock()
        mock_collection.query.hybrid.return_value = MagicMock(objects=[obj2, obj1])
        mock_weaviate_client["client"].collections.get.return_value = mock_collection

        from video_research_mcp.tools.knowledge import knowledge_search
        result = await knowledge_search(query="test", collections=["VideoAnalyses"])
        assert len(result["results"]) == 2
        assert result["results"][0]["score"] >= result["results"][1]["score"]


class TestKnowledgeRelated:
    """Tests for knowledge_related tool."""

    async def test_returns_empty_when_disabled(self, mock_weaviate_disabled):
        """knowledge_related returns empty result when Weaviate not configured."""
        from video_research_mcp.tools.knowledge import knowledge_related
        result = await knowledge_related(object_id="test-uuid", collection="VideoAnalyses")
        assert result["related"] == []

    async def test_excludes_self_from_results(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_related excludes the source object from results."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        self_obj = MagicMock()
        self_obj.uuid = "source-uuid"
        self_obj.properties = {"title": "Self"}
        self_obj.metadata = MagicMock(distance=0.0)

        other_obj = MagicMock()
        other_obj.uuid = "other-uuid"
        other_obj.properties = {"title": "Other"}
        other_obj.metadata = MagicMock(distance=0.3)

        mock_collection = MagicMock()
        mock_collection.query.near_object.return_value = MagicMock(objects=[self_obj, other_obj])
        mock_weaviate_client["client"].collections.get.return_value = mock_collection

        from video_research_mcp.tools.knowledge import knowledge_related
        result = await knowledge_related(object_id="source-uuid", collection="VideoAnalyses")
        assert len(result["related"]) == 1
        assert result["related"][0]["object_id"] == "other-uuid"


class TestKnowledgeStats:
    """Tests for knowledge_stats tool."""

    async def test_returns_empty_when_disabled(self, mock_weaviate_disabled):
        """knowledge_stats returns empty when Weaviate not configured."""
        from video_research_mcp.tools.knowledge import knowledge_stats
        result = await knowledge_stats()
        assert result["total_objects"] == 0

    async def test_returns_stats_for_all_collections(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_stats returns stats for all 7 collections."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agg = MagicMock(total_count=5)
        mock_col = MagicMock()
        mock_col.aggregate.over_all.return_value = mock_agg
        mock_weaviate_client["client"].collections.get.return_value = mock_col

        from video_research_mcp.tools.knowledge import knowledge_stats
        result = await knowledge_stats()
        assert len(result["collections"]) == 7
        assert result["total_objects"] == 35

    async def test_returns_stats_for_single_collection(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_stats returns stats for a single collection."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agg = MagicMock(total_count=10)
        mock_col = MagicMock()
        mock_col.aggregate.over_all.return_value = mock_agg
        mock_weaviate_client["client"].collections.get.return_value = mock_col

        from video_research_mcp.tools.knowledge import knowledge_stats
        result = await knowledge_stats(collection="VideoAnalyses")
        assert len(result["collections"]) == 1
        assert result["collections"][0]["count"] == 10


class TestKnowledgeIngest:
    """Tests for knowledge_ingest tool."""

    async def test_returns_error_when_disabled(self, mock_weaviate_disabled):
        """knowledge_ingest returns error when Weaviate not configured."""
        from video_research_mcp.tools.knowledge import knowledge_ingest
        result = await knowledge_ingest(collection="VideoAnalyses", properties={"title": "x"})
        assert "error" in result

    async def test_returns_ingest_result(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_ingest returns KnowledgeIngestResult dict."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.tools.knowledge import knowledge_ingest
        result = await knowledge_ingest(
            collection="VideoAnalyses",
            properties={"title": "Manual entry", "summary": "Test"},
        )
        assert result["collection"] == "VideoAnalyses"
        assert result["status"] == "success"

    async def test_rejects_unknown_properties(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_ingest rejects properties not in schema."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.tools.knowledge import knowledge_ingest
        result = await knowledge_ingest(
            collection="VideoAnalyses",
            properties={"title": "ok", "totally_fake_field": "bad"},
        )
        assert "error" in result

    async def test_handles_insert_error(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """knowledge_ingest returns error dict on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("Insert failed")

        from video_research_mcp.tools.knowledge import knowledge_ingest
        result = await knowledge_ingest(
            collection="VideoAnalyses",
            properties={"title": "Will fail"},
        )
        assert "error" in result
