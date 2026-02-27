"""Tests for video tools and URL helpers."""

from __future__ import annotations

import pytest

from gemini_research_mcp.tools.video_url import (
    _extract_video_id,
    _normalize_youtube_url,
)
from gemini_research_mcp.tools.video import video_analyze
from gemini_research_mcp.models.video import VideoResult


class TestUrlHelpers:
    def test_normalize_standard_url(self):
        url = "https://www.youtube.com/watch?v=abc123"
        assert _normalize_youtube_url(url) == "https://www.youtube.com/watch?v=abc123"

    def test_normalize_short_url(self):
        url = "https://youtu.be/abc123"
        assert _normalize_youtube_url(url) == "https://www.youtube.com/watch?v=abc123"

    def test_normalize_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=abc123&list=PLxyz&t=30"
        result = _normalize_youtube_url(url)
        assert result == "https://www.youtube.com/watch?v=abc123"

    def test_normalize_with_escapes(self):
        url = "https://www.youtube.com/watch\\?v=abc123"
        assert _normalize_youtube_url(url) == "https://www.youtube.com/watch?v=abc123"

    def test_invalid_url(self):
        with pytest.raises(ValueError, match="Could not extract"):
            _normalize_youtube_url("https://example.com/page")

    def test_extract_video_id(self):
        assert _extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
        assert _extract_video_id("https://youtu.be/xyz789") == "xyz789"
        assert _extract_video_id("https://www.youtube.com/shorts/short123") == "short123"

    def test_extract_video_id_invalid(self):
        with pytest.raises(ValueError):
            _extract_video_id("https://example.com")

    def test_reject_spoofed_youtube_domains(self):
        with pytest.raises(ValueError):
            _extract_video_id("https://notyoutube.com/watch?v=abc123")
        with pytest.raises(ValueError):
            _extract_video_id("https://youtube.com.evil.test/watch?v=abc123")


class TestVideoAnalyze:
    @pytest.mark.asyncio
    async def test_video_analyze_default_schema(self, mock_gemini_client):
        """video_analyze with no custom schema uses VideoResult via generate_structured."""
        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="Test Video",
            summary="A test summary",
            key_points=["point 1"],
            topics=["AI"],
        )

        result = await video_analyze(
            url="https://www.youtube.com/watch?v=abc123",
            use_cache=False,
        )

        assert result["title"] == "Test Video"
        assert result["summary"] == "A test summary"
        assert result["url"] == "https://www.youtube.com/watch?v=abc123"
        mock_gemini_client["generate_structured"].assert_called_once()

    @pytest.mark.asyncio
    async def test_video_analyze_custom_schema(self, mock_gemini_client):
        """video_analyze with custom output_schema uses generate() + json.loads."""
        mock_gemini_client["generate"].return_value = '{"recipes": ["pasta", "salad"]}'

        custom_schema = {"type": "object", "properties": {"recipes": {"type": "array"}}}
        result = await video_analyze(
            url="https://www.youtube.com/watch?v=abc123",
            instruction="List all recipes",
            output_schema=custom_schema,
            use_cache=False,
        )

        assert result["recipes"] == ["pasta", "salad"]
        assert result["url"] == "https://www.youtube.com/watch?v=abc123"
        mock_gemini_client["generate"].assert_called_once()

    @pytest.mark.asyncio
    async def test_video_analyze_invalid_url(self):
        """Invalid URL returns tool error without calling Gemini."""
        result = await video_analyze(url="https://example.com/page")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_video_analyze_with_instruction(self, mock_gemini_client):
        """Custom instruction is forwarded to the Gemini call."""
        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="CLI Video",
            key_points=["use --verbose"],
        )

        result = await video_analyze(
            url="https://www.youtube.com/watch?v=abc123",
            instruction="Extract all CLI commands shown",
            use_cache=False,
        )

        assert result["title"] == "CLI Video"
        call_args = mock_gemini_client["generate_structured"].call_args
        assert call_args is not None
