"""Tests for search tools."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gemini_research_mcp.tools.search import web_search


class TestSearchTools:
    @pytest.mark.asyncio
    async def test_web_search_returns_grounded_sources(self):
        """GIVEN a mocked Gemini response with grounding chunks
        WHEN web_search is called
        THEN it returns the query, response text, and parsed sources.
        """
        response = SimpleNamespace(
            text="Result text",
            candidates=[
                SimpleNamespace(
                    grounding_metadata=SimpleNamespace(
                        grounding_chunks=[
                            SimpleNamespace(web=SimpleNamespace(title="A", uri="https://a.test")),
                            SimpleNamespace(web=SimpleNamespace(title="B", uri="https://b.test")),
                        ]
                    )
                )
            ],
        )
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=response)

        with patch("gemini_research_mcp.tools.search.GeminiClient.get", return_value=client):
            out = await web_search("query", num_results=2)

        assert out["query"] == "query"
        assert out["response"] == "Result text"
        assert len(out["sources"]) == 2
        assert out["sources"][0]["url"] == "https://a.test"

    @pytest.mark.asyncio
    async def test_web_search_no_grounding_metadata(self):
        """GIVEN a response without grounding metadata
        WHEN web_search is called
        THEN it returns query and response without sources.
        """
        response = SimpleNamespace(
            text="Just text",
            candidates=[SimpleNamespace(grounding_metadata=None)],
        )
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=response)

        with patch("gemini_research_mcp.tools.search.GeminiClient.get", return_value=client):
            out = await web_search("test query")

        assert out["query"] == "test query"
        assert out["response"] == "Just text"
        assert "sources" not in out

    @pytest.mark.asyncio
    async def test_web_search_error_returns_tool_error(self):
        """GIVEN a Gemini API exception
        WHEN web_search is called
        THEN it returns a structured tool error dict.
        """
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch("gemini_research_mcp.tools.search.GeminiClient.get", return_value=client):
            out = await web_search("failing query")

        assert "error" in out
        assert out["retryable"] is True
