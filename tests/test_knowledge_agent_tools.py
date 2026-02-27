"""Tests for knowledge_ask and knowledge_query AsyncQueryAgent tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


AGENT_MODULE = "video_research_mcp.tools.knowledge.agent"


class TestKnowledgeAsk:
    """Tests for knowledge_ask tool."""

    async def test_returns_error_when_agent_not_installed(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN weaviate-agents is not installed WHEN knowledge_ask is called THEN returns import error."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        with patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", False):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="What is RAG?")
        assert "error" in result
        assert "weaviate-agents" in result["error"]

    async def test_returns_error_when_weaviate_disabled(self, mock_weaviate_disabled):
        """GIVEN Weaviate is not configured WHEN knowledge_ask is called THEN returns not-configured error."""
        with patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="What is RAG?")
        assert "error" in result
        assert "not configured" in result["error"]

    async def test_returns_answer_with_sources(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent returns answer+sources WHEN knowledge_ask THEN returns structured result."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        source = MagicMock(collection="ResearchFindings", object_id="uuid-abc")
        mock_agent.ask.return_value = MagicMock(
            final_answer="RAG combines retrieval with generation.",
            sources=[source],
        )

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="What is RAG?")

        assert result["query"] == "What is RAG?"
        assert result["answer"] == "RAG combines retrieval with generation."
        assert len(result["sources"]) == 1
        assert result["sources"][0]["collection"] == "ResearchFindings"
        assert result["sources"][0]["object_id"] == "uuid-abc"

    async def test_returns_empty_answer(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent returns no answer WHEN knowledge_ask THEN answer is empty string."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.ask.return_value = MagicMock(final_answer=None, sources=[])

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="Unknown question")

        assert result["answer"] == ""
        assert result["sources"] == []

    async def test_returns_no_sources(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent returns answer without sources WHEN knowledge_ask THEN sources is empty."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.ask.return_value = MagicMock(
            final_answer="An answer", sources=None,
        )

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="test")

        assert result["answer"] == "An answer"
        assert result["sources"] == []

    async def test_passes_collections_to_agent(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN specific collections WHEN knowledge_ask THEN agent receives those collections."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.ask.return_value = MagicMock(final_answer="ok", sources=[])

        mock_get = AsyncMock(return_value=mock_agent)
        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", mock_get),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            await knowledge_ask(
                query="test", collections=["VideoAnalyses", "ResearchFindings"],
            )
            mock_get.assert_called_once_with(["VideoAnalyses", "ResearchFindings"])

    async def test_defaults_to_all_collections(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN no collections specified WHEN knowledge_ask THEN passes None (all collections)."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.ask.return_value = MagicMock(final_answer="ok", sources=[])

        mock_get = AsyncMock(return_value=mock_agent)
        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", mock_get),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            await knowledge_ask(query="test")
            mock_get.assert_called_once_with(None)

    async def test_handles_agent_exception(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent raises WHEN knowledge_ask THEN returns error dict."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.ask.side_effect = RuntimeError("Agent failed")

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_ask
            result = await knowledge_ask(query="test")

        assert "error" in result
        assert "Agent failed" in result["error"]


class TestKnowledgeQuery:
    """Tests for knowledge_query tool."""

    async def test_returns_error_when_agent_not_installed(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN weaviate-agents is not installed WHEN knowledge_query THEN returns import error."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        with patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", False):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="RAG systems")
        assert "error" in result
        assert "weaviate-agents" in result["error"]

    async def test_returns_error_when_weaviate_disabled(self, mock_weaviate_disabled):
        """GIVEN Weaviate is not configured WHEN knowledge_query THEN returns not-configured error."""
        with patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="RAG systems")
        assert "error" in result
        assert "not configured" in result["error"]

    async def test_returns_search_results(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent returns objects WHEN knowledge_query THEN returns KnowledgeQueryResult."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        obj1 = MagicMock(
            collection="ResearchFindings",
            uuid="uuid-1",
            properties={"claim": "RAG improves accuracy"},
        )
        obj2 = MagicMock(
            collection="VideoAnalyses",
            uuid="uuid-2",
            properties={"title": "RAG Tutorial"},
        )
        mock_agent = AsyncMock()
        mock_agent.search.return_value = MagicMock(
            search_results=MagicMock(objects=[obj1, obj2]),
        )

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="RAG systems")

        assert result["query"] == "RAG systems"
        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["collection"] == "ResearchFindings"
        assert result["results"][0]["properties"]["claim"] == "RAG improves accuracy"
        assert result["results"][1]["collection"] == "VideoAnalyses"

    async def test_returns_empty_results(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent returns no objects WHEN knowledge_query THEN returns empty list."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.search.return_value = MagicMock(
            search_results=MagicMock(objects=[]),
        )

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="nonexistent topic")

        assert result["total_results"] == 0
        assert result["results"] == []

    async def test_passes_collections_to_agent(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN specific collections WHEN knowledge_query THEN agent receives them."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.search.return_value = MagicMock(
            search_results=MagicMock(objects=[]),
        )

        mock_get = AsyncMock(return_value=mock_agent)
        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", mock_get),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            await knowledge_query(query="test", collections=["VideoMetadata"])
            mock_get.assert_called_once_with(["VideoMetadata"])

    async def test_passes_limit_to_search(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN custom limit WHEN knowledge_query THEN passes limit to agent.search()."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.search.return_value = MagicMock(
            search_results=MagicMock(objects=[]),
        )

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            await knowledge_query(query="test", limit=25)
            mock_agent.search.assert_called_once_with("test", limit=25)

    async def test_handles_agent_exception(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN AsyncQueryAgent raises WHEN knowledge_query THEN returns error dict."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.search.side_effect = RuntimeError("Search failed")

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="test")

        assert "error" in result
        assert "Search failed" in result["error"]

    async def test_handles_none_search_results(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """GIVEN search_results is None WHEN knowledge_query THEN returns empty results."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_agent = AsyncMock()
        mock_agent.search.return_value = MagicMock(search_results=None)

        with (
            patch(f"{AGENT_MODULE}._HAS_QUERY_AGENT", True),
            patch(f"{AGENT_MODULE}._get_query_agent", new_callable=AsyncMock, return_value=mock_agent),
        ):
            from video_research_mcp.tools.knowledge.agent import knowledge_query
            result = await knowledge_query(query="test")

        assert result["total_results"] == 0
        assert result["results"] == []


class TestQueryAgentSingleton:
    """Tests for the _get_query_agent async caching behavior."""

    async def test_caches_by_collection_set(self, mock_weaviate_client):
        """GIVEN same collections WHEN _get_query_agent called twice THEN returns same instance."""
        import asyncio
        with patch(f"{AGENT_MODULE}._query_agents", {}):
            mock_qa_class = MagicMock()
            with (
                patch(f"{AGENT_MODULE}.AsyncQueryAgent", mock_qa_class, create=True),
                patch(f"{AGENT_MODULE}._agent_lock", asyncio.Lock()),
                patch("video_research_mcp.weaviate_client.WeaviateClient.aget", new_callable=AsyncMock, return_value=mock_weaviate_client["client"]),
            ):
                from video_research_mcp.tools.knowledge.agent import _get_query_agent
                agent1 = await _get_query_agent(["VideoAnalyses", "ResearchFindings"])
                agent2 = await _get_query_agent(["ResearchFindings", "VideoAnalyses"])
                # Same sorted tuple + same client → same agent
                assert agent1 is agent2
                assert mock_qa_class.call_count == 1

    async def test_different_collections_get_different_agents(self, mock_weaviate_client):
        """GIVEN different collections WHEN _get_query_agent called THEN returns different instances."""
        import asyncio
        with patch(f"{AGENT_MODULE}._query_agents", {}):
            mock_qa_class = MagicMock()
            with (
                patch(f"{AGENT_MODULE}.AsyncQueryAgent", mock_qa_class, create=True),
                patch(f"{AGENT_MODULE}._agent_lock", asyncio.Lock()),
                patch("video_research_mcp.weaviate_client.WeaviateClient.aget", new_callable=AsyncMock, return_value=mock_weaviate_client["client"]),
            ):
                from video_research_mcp.tools.knowledge.agent import _get_query_agent
                await _get_query_agent(["VideoAnalyses"])
                await _get_query_agent(["ResearchFindings"])
                assert mock_qa_class.call_count == 2

    async def test_invalidates_on_client_change(self, mock_weaviate_client):
        """GIVEN cached agent WHEN WeaviateClient.aget() returns new client THEN creates new agent."""
        import asyncio
        client_a = MagicMock(name="client-A")
        client_b = MagicMock(name="client-B")
        agent_a = MagicMock(name="agent-A")
        agent_b = MagicMock(name="agent-B")

        with patch(f"{AGENT_MODULE}._query_agents", {}):
            mock_qa_class = MagicMock(side_effect=[agent_a, agent_b])
            with (
                patch(f"{AGENT_MODULE}.AsyncQueryAgent", mock_qa_class, create=True),
                patch(f"{AGENT_MODULE}._agent_lock", asyncio.Lock()),
            ):
                from video_research_mcp.tools.knowledge.agent import _get_query_agent

                # First call caches agent bound to client_a
                with patch("video_research_mcp.weaviate_client.WeaviateClient.aget", new_callable=AsyncMock, return_value=client_a):
                    result_a = await _get_query_agent(["VideoAnalyses"])

                # Second call with new client → cache miss → new agent
                with patch("video_research_mcp.weaviate_client.WeaviateClient.aget", new_callable=AsyncMock, return_value=client_b):
                    result_b = await _get_query_agent(["VideoAnalyses"])

                assert result_a is agent_a
                assert result_b is agent_b
                assert mock_qa_class.call_count == 2
