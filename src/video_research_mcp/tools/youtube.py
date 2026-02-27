"""YouTube Data API tools — metadata and playlist retrieval."""

from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import parse_qs, urlparse

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from ..errors import make_tool_error
from ..types import PlaylistUrl, YouTubeUrl
from ..youtube import YouTubeClient
from .video_url import _extract_video_id, _is_youtube_host

logger = logging.getLogger(__name__)
youtube_server = FastMCP("youtube")


def _extract_playlist_id(url: str) -> str:
    """Extract playlist ID from a YouTube playlist or video+playlist URL.

    Supports:
        - https://www.youtube.com/playlist?list=PLxxxxxx
        - https://www.youtube.com/watch?v=xxx&list=PLxxxxxx

    Raises:
        ValueError: If not a YouTube URL or no playlist ID found.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    if not _is_youtube_host(host):
        raise ValueError(f"Not a YouTube URL: {url}")
    playlist_id = parse_qs(parsed.query).get("list", [None])[0]
    if not playlist_id:
        raise ValueError(
            f"Could not extract playlist ID from URL: {url}. "
            "Expected a 'list' query parameter."
        )
    return playlist_id


@youtube_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def video_metadata(
    url: YouTubeUrl,
) -> dict:
    """Fetch YouTube video metadata without Gemini analysis.

    Returns title, description, view/like/comment counts, duration,
    tags, channel info, category, and language. Costs 1 YouTube API
    unit, 0 Gemini units.

    Args:
        url: YouTube video URL.

    Returns:
        Dict matching VideoMetadata schema.
    """
    try:
        video_id = _extract_video_id(url)
    except ValueError as exc:
        return make_tool_error(exc)

    try:
        meta = await YouTubeClient.video_metadata(video_id)
        return meta.model_dump()
    except Exception as exc:
        return make_tool_error(exc)


@youtube_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def video_playlist(
    url: PlaylistUrl,
    max_items: Annotated[int, Field(
        ge=1, le=50, description="Maximum videos to return"
    )] = 20,
) -> dict:
    """Get video IDs and titles from a YouTube playlist.

    Results can be passed to video_analyze for batch analysis.
    Costs 1 YouTube API unit per page (max 50 items/page).

    Args:
        url: YouTube playlist URL.
        max_items: Maximum number of playlist items to return.

    Returns:
        Dict matching PlaylistInfo schema.
    """
    try:
        playlist_id = _extract_playlist_id(url)
    except ValueError as exc:
        return make_tool_error(exc)

    try:
        info = await YouTubeClient.playlist_items(playlist_id, max_items)
        return info.model_dump()
    except Exception as exc:
        return make_tool_error(exc)
