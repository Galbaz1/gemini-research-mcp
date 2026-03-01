"""YouTube Data API v3 client — metadata, comments, playlists.

Thin async-compatible wrapper using google-api-python-client (sync)
wrapped in asyncio.to_thread(). Reuses GEMINI_API_KEY from config.
"""

from __future__ import annotations

import asyncio
import logging
import re

from .config import get_config
from .models.youtube import (
    PlaylistInfo,
    PlaylistItem,
    VideoMetadata,
    YOUTUBE_CATEGORIES,
)

logger = logging.getLogger(__name__)


def _parse_iso8601_duration(duration: str) -> int:
    """Parse ISO 8601 duration (PT4M13S) into total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _format_duration(total_seconds: int) -> str:
    """Format seconds as human-readable duration (e.g. 4:13 or 1:02:03)."""
    if total_seconds <= 0:
        return "0:00"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class YouTubeClient:
    """Singleton YouTube Data API v3 client."""

    _service = None

    @classmethod
    def get(cls):
        """Get or create the YouTube API service (lazy singleton)."""
        if cls._service is None:
            from googleapiclient.discovery import build

            cfg = get_config()
            api_key = cfg.youtube_api_key or cfg.gemini_api_key
            cls._service = build(
                "youtube", "v3", developerKey=api_key, cache_discovery=False,
            )
        return cls._service

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._service = None

    @classmethod
    async def video_metadata(cls, video_id: str) -> VideoMetadata:
        """Fetch video metadata (title, stats, duration, channel, tags).

        Args:
            video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ').

        Returns:
            Validated VideoMetadata model.
        """

        def _fetch():
            svc = cls.get()
            resp = svc.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id,
            ).execute()
            return resp

        resp = await asyncio.to_thread(_fetch)
        items = resp.get("items", [])
        if not items:
            raise ValueError(f"Video not found: {video_id}")

        item = items[0]
        snippet = item.get("snippet", {})
        details = item.get("contentDetails", {})
        stats = item.get("statistics", {})

        duration_secs = _parse_iso8601_duration(details.get("duration", ""))
        category_id = snippet.get("categoryId", "")

        return VideoMetadata(
            video_id=video_id,
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            channel_id=snippet.get("channelId", ""),
            channel_title=snippet.get("channelTitle", ""),
            published_at=snippet.get("publishedAt", ""),
            tags=snippet.get("tags", []),
            view_count=int(stats.get("viewCount", 0)),
            like_count=int(stats.get("likeCount", 0)),
            comment_count=int(stats.get("commentCount", 0)),
            duration_seconds=duration_secs,
            duration_display=_format_duration(duration_secs),
            category=YOUTUBE_CATEGORIES.get(category_id, category_id),
            definition=details.get("definition", ""),
            has_captions=details.get("caption", "false") == "true",
            default_language=snippet.get("defaultLanguage", ""),
        )

    @classmethod
    async def video_comments(
        cls, video_id: str, max_comments: int = 200
    ) -> list[dict]:
        """Fetch top comments sorted by relevance.

        Args:
            video_id: YouTube video ID.
            max_comments: Maximum number of comments to fetch.

        Returns:
            List of dicts with text, likes, author keys.
        """

        def _fetch():
            svc = cls.get()
            comments: list[dict] = []
            request = svc.commentThreads().list(
                part="snippet",
                videoId=video_id,
                order="relevance",
                maxResults=min(100, max_comments),
                textFormat="plainText",
            )
            while request and len(comments) < max_comments:
                response = request.execute()
                for item in response.get("items", []):
                    top = item.get("snippet", {}).get("topLevelComment", {})
                    snip = top.get("snippet", {})
                    comments.append({
                        "text": snip.get("textDisplay", ""),
                        "likes": snip.get("likeCount", 0),
                        "author": snip.get("authorDisplayName", ""),
                    })
                request = svc.commentThreads().list_next(request, response)
            return comments[:max_comments]

        return await asyncio.to_thread(_fetch)

    @classmethod
    async def playlist_items(
        cls, playlist_id: str, max_items: int = 50
    ) -> PlaylistInfo:
        """Get video items from a playlist.

        Args:
            playlist_id: YouTube playlist ID (e.g. 'PLrAXtmErZgOe...').
            max_items: Maximum items to return.

        Returns:
            Validated PlaylistInfo model.
        """

        def _fetch():
            svc = cls.get()
            items: list[dict] = []
            request = svc.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=min(50, max_items),
            )
            while request and len(items) < max_items:
                response = request.execute()
                total = response.get("pageInfo", {}).get("totalResults", 0)
                for entry in response.get("items", []):
                    snip = entry.get("snippet", {})
                    resource = snip.get("resourceId", {})
                    items.append({
                        "video_id": resource.get("videoId", ""),
                        "title": snip.get("title", ""),
                        "position": snip.get("position", 0),
                        "published_at": snip.get("publishedAt", ""),
                    })
                request = svc.playlistItems().list_next(request, response)
            return items[:max_items], total

        raw_items, total = await asyncio.to_thread(_fetch)
        return PlaylistInfo(
            playlist_id=playlist_id,
            items=[PlaylistItem(**item) for item in raw_items],
            total_items=total,
        )
