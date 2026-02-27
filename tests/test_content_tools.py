"""Tests for content tools."""

from __future__ import annotations

import pytest

from gemini_research_mcp.models.content import ContentResult
from gemini_research_mcp.tools.content import (
    _build_content_parts,
    content_analyze,
    content_extract,
)


class TestBuildContentParts:
    def test_text_input(self):
        parts, desc = _build_content_parts(text="Hello world")
        assert len(parts) == 1
        assert "text" in desc.lower()

    def test_url_input(self):
        parts, desc = _build_content_parts(url="https://example.com")
        assert len(parts) == 1
        assert "URL" in desc

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            _build_content_parts(file_path="/nonexistent/file.pdf")

    def test_no_input(self):
        with pytest.raises(ValueError, match="at least one"):
            _build_content_parts()

    def test_file_input(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        parts, desc = _build_content_parts(file_path=str(f))
        assert len(parts) == 1
        assert "test.txt" in desc


class TestContentAnalyze:
    @pytest.mark.asyncio
    async def test_text_default_schema(self, mock_gemini_client):
        """content_analyze with text input uses generate_structured."""
        mock_gemini_client["generate_structured"].return_value = ContentResult(
            title="Test",
            summary="A summary",
            key_points=["point 1"],
        )

        result = await content_analyze(text="Some text content")

        assert result["title"] == "Test"
        assert result["summary"] == "A summary"
        mock_gemini_client["generate_structured"].assert_called_once()

    @pytest.mark.asyncio
    async def test_url_uses_url_context(self, mock_gemini_client):
        """content_analyze with URL uses UrlContext tool wiring."""
        mock_gemini_client["generate"].return_value = '{"title": "Page", "summary": "About"}'

        result = await content_analyze(url="https://example.com")

        assert result["title"] == "Page"
        call_kwargs = mock_gemini_client["generate"].call_args.kwargs
        assert call_kwargs["tools"][0].url_context is not None

    @pytest.mark.asyncio
    async def test_no_input_returns_error(self):
        """No content source returns tool error."""
        result = await content_analyze()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_multiple_sources_returns_error(self):
        """Multiple content sources rejected with descriptive error."""
        result = await content_analyze(url="https://example.com", text="some text")
        assert "error" in result
        assert "url" in result["error"]
        assert "text" in result["error"]

    @pytest.mark.asyncio
    async def test_custom_schema(self, mock_gemini_client):
        """content_analyze with custom output_schema uses generate()."""
        mock_gemini_client["generate"].return_value = '{"citations": ["Ref A"]}'

        schema = {"type": "object", "properties": {"citations": {"type": "array"}}}
        result = await content_analyze(
            text="Some paper text",
            instruction="List all citations",
            output_schema=schema,
        )

        assert result["citations"] == ["Ref A"]

    @pytest.mark.asyncio
    async def test_url_fallback_on_structured_failure(self, mock_gemini_client):
        """URL path falls back to two-step when structured + UrlContext fails."""
        # First call (structured + UrlContext) fails, second (unstructured) succeeds
        mock_gemini_client["generate"].side_effect = [
            Exception("structured output not supported with UrlContext"),
            "Some unstructured text about the page",
        ]
        mock_gemini_client["generate_structured"].return_value = ContentResult(
            title="Fallback",
            summary="Reshaped from unstructured",
        )

        result = await content_analyze(url="https://example.com")

        assert result["title"] == "Fallback"
        assert mock_gemini_client["generate_structured"].call_count == 1


class TestContentExtract:
    @pytest.mark.asyncio
    async def test_extract_returns_parsed_json(self, mock_gemini_client):
        """content_extract returns parsed JSON matching schema."""
        mock_gemini_client["generate"].return_value = '{"name": "Alice", "age": 30}'

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        result = await content_extract(content="Alice is 30 years old.", schema=schema)

        assert result["name"] == "Alice"
        assert result["age"] == 30

    @pytest.mark.asyncio
    async def test_extract_json_decode_error(self, mock_gemini_client):
        """content_extract returns error dict on malformed JSON."""
        mock_gemini_client["generate"].return_value = "not valid json"

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = await content_extract(content="some text", schema=schema)

        assert "error" in result
        assert "raw_response" in result
