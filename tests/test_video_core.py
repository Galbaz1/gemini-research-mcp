"""Tests for the shared video analysis pipeline."""

from __future__ import annotations

from google.genai import types

import pytest

from video_research_mcp.models.video import VideoResult
from video_research_mcp.tools.video_core import analyze_video


def _make_content(text: str = "test") -> types.Content:
    return types.Content(parts=[types.Part(text=text)])


class TestAnalyzeVideo:
    @pytest.mark.asyncio
    async def test_default_schema(self, mock_gemini_client):
        """Uses generate_structured with VideoResult when no custom schema."""
        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="Test",
            summary="Summary",
        )

        result = await analyze_video(
            _make_content(),
            instruction="summarize",
            content_id="vid123",
            source_label="https://youtube.com/watch?v=vid123",
            use_cache=False,
        )

        assert result["title"] == "Test"
        assert result["source"] == "https://youtube.com/watch?v=vid123"
        mock_gemini_client["generate_structured"].assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_schema(self, mock_gemini_client):
        """Uses generate with custom schema when output_schema provided."""
        mock_gemini_client["generate"].return_value = '{"items": [1, 2]}'
        schema = {"type": "object", "properties": {"items": {"type": "array"}}}

        result = await analyze_video(
            _make_content(),
            instruction="extract items",
            content_id="vid456",
            source_label="/path/to/file.mp4",
            output_schema=schema,
            use_cache=False,
        )

        assert result["items"] == [1, 2]
        assert result["source"] == "/path/to/file.mp4"
        mock_gemini_client["generate"].assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_gemini_client, tmp_path, monkeypatch):
        """Returns cached result without calling Gemini."""
        from video_research_mcp import cache

        monkeypatch.setattr(cache, "_cache_dir", lambda: tmp_path)
        cache.save("cached_id", "video_analyze", "test-model", {"title": "Cached"}, instruction="test")

        # Patch get_config to return matching model
        from video_research_mcp.config import ServerConfig
        from unittest.mock import patch

        cfg = ServerConfig(gemini_api_key="test-key-not-real", default_model="test-model")
        with patch("video_research_mcp.tools.video_core.get_config", return_value=cfg):
            result = await analyze_video(
                _make_content(),
                instruction="test",
                content_id="cached_id",
                source_label="some-url",
                use_cache=True,
            )

        assert result["title"] == "Cached"
        assert result["cached"] is True
        mock_gemini_client["generate_structured"].assert_not_called()
        mock_gemini_client["generate"].assert_not_called()
