"""YouTube URL validation and content helpers."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from google.genai import types


def _is_youtube_host(host: str) -> bool:
    host = host.lower().split(":", 1)[0]
    return host == "youtube.com" or host.endswith(".youtube.com")


def _is_youtu_be_host(host: str) -> bool:
    host = host.lower().split(":", 1)[0]
    return host == "youtu.be" or host == "www.youtu.be"


def _extract_video_id_from_parsed(parsed) -> str | None:
    host = parsed.netloc.lower().split(":", 1)[0]
    if _is_youtu_be_host(host):
        return parsed.path.strip("/").split("/", 1)[0] or None

    if not _is_youtube_host(host):
        return None

    video_id = parse_qs(parsed.query).get("v", [None])[0]
    if video_id:
        return video_id

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
        return parts[1]
    return None


def _normalize_youtube_url(url: str) -> str:
    """Normalize to ``https://www.youtube.com/watch?v=VIDEO_ID``."""
    url = url.replace("\\", "")
    parsed = urlparse(url)
    video_id = _extract_video_id_from_parsed(parsed)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    video_id = video_id.split("&")[0].split("?")[0]
    return f"https://www.youtube.com/watch?v={video_id}"


def _extract_video_id(url: str) -> str:
    url = url.replace("\\", "")
    parsed = urlparse(url)
    vid = _extract_video_id_from_parsed(parsed)
    if not vid:
        raise ValueError(f"Not a YouTube URL: {url}")
    return vid.split("&")[0].split("?")[0]


def _video_content(url: str, prompt: str) -> types.Content:
    """Build a Content with video FileData + text prompt."""
    return types.Content(
        parts=[
            types.Part(file_data=types.FileData(file_uri=url)),
            types.Part(text=prompt),
        ]
    )
