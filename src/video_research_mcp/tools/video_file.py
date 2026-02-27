"""Local video file helpers — MIME detection, hashing, content building, File API upload."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from google.genai import types

from ..client import GeminiClient

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".mpeg": "video/mpeg",
    ".wmv": "video/x-ms-wmv",
    ".3gpp": "video/3gpp",
}

LARGE_FILE_THRESHOLD = 20 * 1024 * 1024  # 20 MB


def _video_mime_type(path: Path) -> str:
    """Return MIME type for a video file, or raise ValueError if unsupported."""
    ext = path.suffix.lower()
    mime = SUPPORTED_VIDEO_EXTENSIONS.get(ext)
    if not mime:
        allowed = ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        raise ValueError(f"Unsupported video extension '{ext}'. Supported: {allowed}")
    return mime


def _file_content_hash(path: Path) -> str:
    """SHA-256 of file contents, truncated to 16 hex chars."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _validate_video_path(file_path: str) -> tuple[Path, str]:
    """Validate path exists and has supported extension. Returns (path, mime)."""
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")
    if not p.is_file():
        raise ValueError(f"Not a file: {file_path}")
    mime = _video_mime_type(p)
    return p, mime


async def _upload_large_file(path: Path, mime_type: str) -> str:
    """Upload via Gemini File API, return the file URI."""
    client = GeminiClient.get()
    uploaded = await client.aio.files.upload(
        file=path,
        config=types.UploadFileConfig(mime_type=mime_type),
    )
    logger.info("Uploaded %s → %s", path.name, uploaded.uri)
    return uploaded.uri


async def _video_file_content(file_path: str, prompt: str) -> tuple[types.Content, str]:
    """Build Content for a local video file.

    Small files (<20 MB) use inline Part.from_bytes.
    Large files are uploaded via the File API.

    Returns:
        (content, content_id) where content_id is the SHA-256 hash prefix.
    """
    p, mime = _validate_video_path(file_path)
    content_id = _file_content_hash(p)
    size = p.stat().st_size

    if size >= LARGE_FILE_THRESHOLD:
        uri = await _upload_large_file(p, mime)
        parts = [types.Part(file_data=types.FileData(file_uri=uri))]
    else:
        data = await asyncio.to_thread(p.read_bytes)
        parts = [types.Part.from_bytes(data=data, mime_type=mime)]

    parts.append(types.Part(text=prompt))
    return types.Content(parts=parts), content_id


async def _video_file_uri(file_path: str) -> tuple[str, str]:
    """Upload a local video and return (file_uri, content_id) for sessions.

    Sessions always upload (even small files) to get a stable URI for multi-turn replay.
    """
    p, mime = _validate_video_path(file_path)
    content_id = _file_content_hash(p)
    uri = await _upload_large_file(p, mime)
    return uri, content_id
