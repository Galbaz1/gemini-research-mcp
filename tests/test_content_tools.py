"""Tests for content tool helpers."""

from __future__ import annotations

import pytest

from gemini_research_mcp.tools.content import _build_content_parts


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
