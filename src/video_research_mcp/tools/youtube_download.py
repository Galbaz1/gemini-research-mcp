"""YouTube video download via yt-dlp subprocess.

Downloads YouTube videos to a local cache directory for File API upload.
No Python yt-dlp dependency — calls the binary directly.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from ..config import get_config

logger = logging.getLogger(__name__)

_FORMAT = "mp4[height<=720]/mp4/best[ext=mp4]"


def _download_dir() -> Path:
    """Return the download cache directory, creating it if needed."""
    d = Path(get_config().cache_dir) / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def download_youtube_video(video_id: str) -> Path:
    """Download a YouTube video via yt-dlp to local cache.

    Reuses cached download if the file already exists. Downloads at
    720p max to balance quality with upload/processing time.

    Args:
        video_id: YouTube video ID (e.g. "dQw4w9WgXcQ").

    Returns:
        Path to the downloaded .mp4 file.

    Raises:
        RuntimeError: If yt-dlp is not installed or download fails.
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp not found. Install it: brew install yt-dlp (macOS) "
            "or pip install yt-dlp"
        )

    output_path = _download_dir() / f"{video_id}.mp4"

    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("Download cache hit: %s", output_path.name)
        return output_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-f", _FORMAT,
        "-o", str(output_path),
        url,
    ]

    logger.info("Downloading %s via yt-dlp...", video_id)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        # Clean up partial download
        output_path.unlink(missing_ok=True)
        err_msg = stderr.decode().strip() if stderr else "unknown error"
        raise RuntimeError(f"yt-dlp failed for {video_id}: {err_msg}")

    if not output_path.exists():
        raise RuntimeError(
            f"yt-dlp exited successfully but output file not found: {output_path}"
        )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Downloaded %s (%.1f MB)", output_path.name, size_mb)
    return output_path
