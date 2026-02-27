"""Tests for video file helpers — MIME detection, hashing, content building."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from gemini_research_mcp.tools.video_file import (
    LARGE_FILE_THRESHOLD,
    SUPPORTED_VIDEO_EXTENSIONS,
    _file_content_hash,
    _validate_video_path,
    _video_file_content,
    _video_file_uri,
    _video_mime_type,
)


class TestVideoMimeType:
    def test_supported_extensions(self):
        for ext, mime in SUPPORTED_VIDEO_EXTENSIONS.items():
            assert _video_mime_type(Path(f"video{ext}")) == mime

    def test_case_insensitive(self):
        assert _video_mime_type(Path("video.MP4")) == "video/mp4"
        assert _video_mime_type(Path("video.WebM")) == "video/webm"

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="Unsupported video extension"):
            _video_mime_type(Path("file.txt"))

    def test_no_extension(self):
        with pytest.raises(ValueError, match="Unsupported video extension"):
            _video_mime_type(Path("noextension"))


class TestFileContentHash:
    def test_deterministic(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"video content")
        h1 = _file_content_hash(f)
        h2 = _file_content_hash(f)
        assert h1 == h2
        assert len(h1) == 16

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert _file_content_hash(f1) != _file_content_hash(f2)


class TestValidateVideoPath:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "clip.mp4"
        f.write_bytes(b"\x00" * 10)
        p, mime = _validate_video_path(str(f))
        assert p == f
        assert mime == "video/mp4"

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            _validate_video_path(str(tmp_path / "missing.mp4"))

    def test_not_a_file(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="Not a file"):
            _validate_video_path(str(d))

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported video extension"):
            _validate_video_path(str(f))


class TestVideoFileContent:
    @pytest.mark.asyncio
    async def test_small_file_uses_inline_bytes(self, tmp_path, mock_gemini_client):
        """Files under threshold use Part.from_bytes (no File API upload)."""
        f = tmp_path / "small.mp4"
        f.write_bytes(b"\x00" * 100)

        content, content_id = await _video_file_content(str(f), "summarize")

        assert content_id == _file_content_hash(f)
        assert len(content.parts) == 2
        # First part: inline bytes (no file_data attribute)
        assert content.parts[0].inline_data is not None
        # Second part: text prompt
        assert content.parts[1].text == "summarize"

    @pytest.mark.asyncio
    async def test_large_file_uses_file_api(self, tmp_path, mock_gemini_client):
        """Files at or above threshold upload via File API."""
        f = tmp_path / "big.mp4"
        f.write_bytes(b"\x00" * LARGE_FILE_THRESHOLD)

        uploaded = MagicMock()
        uploaded.uri = "https://generativelanguage.googleapis.com/v1/files/abc123"
        mock_gemini_client["client"].aio.files.upload = AsyncMock(return_value=uploaded)

        content, content_id = await _video_file_content(str(f), "analyze")

        assert content.parts[0].file_data.file_uri == uploaded.uri
        assert content.parts[1].text == "analyze"
        mock_gemini_client["client"].aio.files.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_not_found(self, mock_gemini_client):
        with pytest.raises(FileNotFoundError):
            await _video_file_content("/nonexistent/video.mp4", "test")


class TestVideoFileUri:
    @pytest.mark.asyncio
    async def test_always_uploads(self, tmp_path, mock_gemini_client):
        """Sessions always upload to get a stable URI, even for small files."""
        f = tmp_path / "tiny.mp4"
        f.write_bytes(b"\x00" * 50)

        uploaded = MagicMock()
        uploaded.uri = "https://generativelanguage.googleapis.com/v1/files/xyz"
        mock_gemini_client["client"].aio.files.upload = AsyncMock(return_value=uploaded)

        uri, content_id = await _video_file_uri(str(f))

        assert uri == uploaded.uri
        assert content_id == _file_content_hash(f)
        mock_gemini_client["client"].aio.files.upload.assert_called_once()
