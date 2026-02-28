"""Tests for YouTube download via yt-dlp subprocess wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import video_research_mcp.config as cfg_mod
from video_research_mcp.tools.youtube_download import download_youtube_video

TEST_VIDEO_ID = "dQw4w9WgXcQ"


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


@pytest.fixture()
def download_dir(tmp_path, monkeypatch):
    """Redirect download directory to a temp path."""
    dl_dir = tmp_path / "downloads"
    dl_dir.mkdir()
    monkeypatch.setattr(
        "video_research_mcp.tools.youtube_download._download_dir",
        lambda: dl_dir,
    )
    return dl_dir


class TestDownloadYoutubeVideo:
    async def test_raises_when_ytdlp_not_found(self, download_dir):
        """GIVEN yt-dlp not installed WHEN download called THEN raises RuntimeError."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="yt-dlp not found"):
                await download_youtube_video(TEST_VIDEO_ID)

    async def test_returns_cached_download(self, download_dir):
        """GIVEN file already exists WHEN download called THEN skips re-download."""
        cached_file = download_dir / f"{TEST_VIDEO_ID}.mp4"
        cached_file.write_bytes(b"fake video content")

        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            result = await download_youtube_video(TEST_VIDEO_ID)

        assert result == cached_file

    async def test_download_succeeds(self, download_dir):
        """GIVEN yt-dlp succeeds WHEN download called THEN returns path to file."""
        output_path = download_dir / f"{TEST_VIDEO_ID}.mp4"

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        async def fake_subprocess(*args, **kwargs):
            # Simulate yt-dlp writing the output file
            output_path.write_bytes(b"downloaded video data")
            return mock_proc

        with (
            patch("shutil.which", return_value="/usr/bin/yt-dlp"),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=fake_subprocess,
            ),
        ):
            result = await download_youtube_video(TEST_VIDEO_ID)

        assert result == output_path
        assert result.exists()

    async def test_download_fails_with_error(self, download_dir):
        """GIVEN yt-dlp exits with error WHEN download called THEN raises RuntimeError."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Video unavailable"))

        with (
            patch("shutil.which", return_value="/usr/bin/yt-dlp"),
            patch(
                "asyncio.create_subprocess_exec",
                AsyncMock(return_value=mock_proc),
            ),
        ):
            with pytest.raises(RuntimeError, match="Video unavailable"):
                await download_youtube_video(TEST_VIDEO_ID)

    async def test_skips_empty_cached_file(self, download_dir):
        """GIVEN an empty cached file WHEN download called THEN re-downloads."""
        cached_file = download_dir / f"{TEST_VIDEO_ID}.mp4"
        cached_file.write_bytes(b"")  # empty = partial/failed download

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        async def fake_subprocess(*args, **kwargs):
            cached_file.write_bytes(b"fresh download")
            return mock_proc

        with (
            patch("shutil.which", return_value="/usr/bin/yt-dlp"),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=fake_subprocess,
            ),
        ):
            result = await download_youtube_video(TEST_VIDEO_ID)

        assert result == cached_file
        assert result.read_bytes() == b"fresh download"
