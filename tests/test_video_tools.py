"""Tests for video tool helpers (URL parsing, response parsing)."""

from __future__ import annotations

import pytest

from gemini_research_mcp.tools.video import (
    _extract_video_id,
    _normalize_youtube_url,
    _parse_labeled_line,
    _parse_list_from_label,
    _parse_markdown_section,
)


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

    def test_extract_video_id_invalid(self):
        with pytest.raises(ValueError):
            _extract_video_id("https://example.com")


class TestParsers:
    def test_parse_labeled_line(self):
        text = "TITLE: My Video Title\nSUMMARY: This is the summary"
        assert _parse_labeled_line(text, "TITLE") == "My Video Title"
        assert _parse_labeled_line(text, "SUMMARY") == "This is the summary"

    def test_parse_labeled_line_with_markdown(self):
        text = "**TITLE**: A **bold** title\nSUMMARY: text"
        result = _parse_labeled_line(text, "TITLE")
        assert "bold" in result

    def test_parse_labeled_line_missing(self):
        assert _parse_labeled_line("nothing here", "TITLE") == ""

    def test_parse_list_comma(self):
        text = "THEMES: artificial intelligence, machine learning, deep learning"
        result = _parse_list_from_label(text, "THEMES")
        assert len(result) == 3
        assert "artificial intelligence" in result[0]

    def test_parse_list_filters_short_items(self):
        """Items ≤2 chars are filtered (noise reduction from original youtube_agent)."""
        text = "THEMES: AI, machine learning"
        result = _parse_list_from_label(text, "THEMES")
        assert len(result) == 1  # "AI" is only 2 chars, filtered

    def test_parse_list_pipe(self):
        text = "COMMANDS: npm install | pip install | cargo build"
        result = _parse_list_from_label(text, "COMMANDS")
        assert len(result) == 3

    def test_parse_markdown_section(self):
        text = """### COMMANDS
`npm install` | Install dependencies
`npm run build` | Build project

### TOOLS
Something else"""
        result = _parse_markdown_section(text, "COMMANDS")
        assert len(result) == 2
        assert "npm install" in result[0]
