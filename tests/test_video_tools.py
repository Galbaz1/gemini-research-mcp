"""Tests for video tools and URL helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from gemini_research_mcp.models.video import VideoResult
from gemini_research_mcp.tools.video import (
    video_analyze,
    video_batch_analyze,
    video_create_session,
)
from gemini_research_mcp.tools.video_url import (
    _extract_video_id,
    _normalize_youtube_url,
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
        assert result["source"] == "https://www.youtube.com/watch?v=abc123"
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
        assert result["source"] == "https://www.youtube.com/watch?v=abc123"
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

    @pytest.mark.asyncio
    async def test_video_analyze_no_source_returns_error(self):
        """Omitting both url and file_path returns validation error."""
        result = await video_analyze()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_video_analyze_both_sources_returns_error(self):
        """Providing both url and file_path returns validation error."""
        result = await video_analyze(
            url="https://www.youtube.com/watch?v=abc123",
            file_path="/some/video.mp4",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_video_analyze_local_file(self, tmp_path, mock_gemini_client):
        """video_analyze with file_path uses local file pipeline."""
        f = tmp_path / "clip.mp4"
        f.write_bytes(b"\x00" * 100)

        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="Local Video",
            summary="Local summary",
        )

        result = await video_analyze(file_path=str(f), use_cache=False)

        assert result["title"] == "Local Video"
        assert result["source"] == str(f)
        mock_gemini_client["generate_structured"].assert_called_once()

    @pytest.mark.asyncio
    async def test_video_analyze_missing_file(self):
        """Non-existent file returns FILE_NOT_FOUND error."""
        result = await video_analyze(file_path="/nonexistent/clip.mp4")
        assert "error" in result
        assert result["category"] == "FILE_NOT_FOUND"


class TestVideoCreateSession:
    @pytest.mark.asyncio
    async def test_create_session_youtube(self, mock_gemini_client):
        """YouTube URL creates session with source_type='youtube'."""
        mock_gemini_client["generate"].return_value = "Test Title"

        result = await video_create_session(
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result["session_id"]
        assert result["status"] == "created"
        assert result["source_type"] == "youtube"

    @pytest.mark.asyncio
    async def test_create_session_local_file(self, tmp_path, mock_gemini_client):
        """Local file creates session with source_type='local'."""
        f = tmp_path / "talk.mp4"
        f.write_bytes(b"\x00" * 50)

        uploaded = MagicMock()
        uploaded.uri = "https://generativelanguage.googleapis.com/v1/files/xyz"
        mock_gemini_client["client"].aio.files.upload = AsyncMock(return_value=uploaded)
        mock_gemini_client["generate"].return_value = "Local Talk"

        result = await video_create_session(file_path=str(f))

        assert result["session_id"]
        assert result["source_type"] == "local"

    @pytest.mark.asyncio
    async def test_create_session_no_source(self):
        """Omitting both url and file_path returns error."""
        result = await video_create_session()
        assert "error" in result


class TestVideoBatchAnalyze:
    @pytest.mark.asyncio
    async def test_batch_analyze_directory(self, tmp_path, mock_gemini_client):
        """Processes multiple video files in a directory."""
        for name in ["a.mp4", "b.webm", "c.txt"]:
            (tmp_path / name).write_bytes(b"\x00" * 50)

        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="Batch",
            summary="Result",
        )

        result = await video_batch_analyze(
            directory=str(tmp_path),
            instruction="summarize",
        )

        assert result["total_files"] == 2  # .txt excluded
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_batch_analyze_empty_directory(self, tmp_path, mock_gemini_client):
        """Empty directory returns zero counts."""
        result = await video_batch_analyze(directory=str(tmp_path))

        assert result["total_files"] == 0
        assert result["successful"] == 0

    @pytest.mark.asyncio
    async def test_batch_analyze_not_a_directory(self, tmp_path):
        """Non-directory path returns error."""
        f = tmp_path / "file.mp4"
        f.write_bytes(b"\x00")
        result = await video_batch_analyze(directory=str(f))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_batch_analyze_respects_max_files(self, tmp_path, mock_gemini_client):
        """max_files limits the number of processed files."""
        for i in range(5):
            (tmp_path / f"v{i}.mp4").write_bytes(b"\x00" * 50)

        mock_gemini_client["generate_structured"].return_value = VideoResult(title="X")

        result = await video_batch_analyze(
            directory=str(tmp_path),
            max_files=2,
        )

        assert result["total_files"] == 2

    @pytest.mark.asyncio
    async def test_batch_analyze_glob_pattern(self, tmp_path, mock_gemini_client):
        """glob_pattern filters which files are matched."""
        (tmp_path / "intro.mp4").write_bytes(b"\x00" * 50)
        (tmp_path / "outro.mp4").write_bytes(b"\x00" * 50)
        (tmp_path / "clip.webm").write_bytes(b"\x00" * 50)

        mock_gemini_client["generate_structured"].return_value = VideoResult(title="X")

        result = await video_batch_analyze(
            directory=str(tmp_path),
            glob_pattern="*.mp4",
        )

        assert result["total_files"] == 2
        names = [i["file_name"] for i in result["items"]]
        assert "clip.webm" not in names
