"""YouTube Data API models — metadata and playlist schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

# YouTube video category IDs → human-readable labels (static, rarely changes).
YOUTUBE_CATEGORIES: dict[str, str] = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


class VideoMetadata(BaseModel):
    """Ground-truth metadata from the YouTube Data API."""

    video_id: str
    title: str = ""
    description: str = ""
    channel_id: str = ""
    channel_title: str = ""
    published_at: str = ""
    tags: list[str] = Field(default_factory=list)
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    duration_seconds: int = 0
    duration_display: str = ""
    category: str = ""
    definition: str = ""
    has_captions: bool = False
    default_language: str = ""


class PlaylistItem(BaseModel):
    """A single video entry in a playlist."""

    video_id: str
    title: str = ""
    position: int = 0
    published_at: str = ""


class PlaylistInfo(BaseModel):
    """Playlist metadata with video items."""

    playlist_id: str
    items: list[PlaylistItem] = Field(default_factory=list)
    total_items: int = 0
