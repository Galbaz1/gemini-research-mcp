"""Video session tools — create and continue multi-turn video exploration sessions."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from google.genai import types
from mcp.types import ToolAnnotations
from pydantic import Field

from ..client import GeminiClient
from .. import context_cache
from ..retry import with_retry
from ..config import get_config
from ..errors import make_tool_error
from ..models.video import SessionInfo, SessionResponse
from ..sessions import session_store
from ..types import VideoFilePath, YouTubeUrl
from ..youtube import YouTubeClient
from .video_url import _extract_video_id, _normalize_youtube_url, _video_content
from .video_file import _video_file_uri
from ._video_server import video_server

logger = logging.getLogger(__name__)


@video_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def video_create_session(
    url: YouTubeUrl | None = None,
    file_path: VideoFilePath | None = None,
    description: Annotated[str, Field(description="Session purpose or focus area")] = "",
) -> dict:
    """Create a persistent session for multi-turn video exploration.

    Provide exactly one of url or file_path.

    Args:
        url: YouTube video URL.
        file_path: Path to a local video file.
        description: Optional focus area for the session.

    Returns:
        Dict with session_id, status, video_title, and source_type.
    """
    try:
        sources = sum(x is not None for x in (url, file_path))
        if sources == 0:
            raise ValueError("Provide exactly one of: url or file_path")
        if sources > 1:
            raise ValueError("Provide exactly one of: url or file_path — got both")
    except ValueError as exc:
        return make_tool_error(exc)

    try:
        if url:
            clean_url = _normalize_youtube_url(url)
            source_type = "youtube"
            content_id = _extract_video_id(url)
        else:
            uri, content_id = await _video_file_uri(file_path)
            clean_url = uri
            source_type = "local"
    except (ValueError, FileNotFoundError) as exc:
        return make_tool_error(exc)

    title = ""
    if source_type == "youtube":
        try:
            video_id = _extract_video_id(url)
            meta = await YouTubeClient.video_metadata(video_id)
            title = meta.title
        except Exception:
            logger.debug("YouTube API title fetch failed, falling back to Gemini")

    if not title:
        try:
            title_content = _video_content(
                clean_url,
                "What is the title of this video? Reply with just the title.",
            )
            resp = await GeminiClient.generate(title_content, thinking_level="low")
            title = resp.strip()
        except Exception:
            title = Path(file_path).stem if file_path else ""

    cfg = get_config()
    model = cfg.default_model
    video_parts = [types.Part(file_data=types.FileData(file_uri=clean_url))]
    cache_name = await context_cache.get_or_create(content_id, video_parts, model) or ""

    session = session_store.create(
        clean_url, "general", video_title=title,
        cache_name=cache_name, model=model,
    )
    return SessionInfo(
        session_id=session.session_id,
        status="created",
        video_title=title,
        source_type=source_type,
        cache_status="cached" if cache_name else "uncached",
    ).model_dump()


@video_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def video_continue_session(
    session_id: Annotated[str, Field(min_length=1, description="Session ID from video_create_session")],
    prompt: Annotated[str, Field(min_length=1, description="Follow-up question or instruction")],
) -> dict:
    """Continue analysis within an existing video session.

    Args:
        session_id: Session ID returned by video_create_session.
        prompt: Follow-up question about the video.

    Returns:
        Dict with response text and turn_count.
    """
    session = session_store.get(session_id)
    if session is None:
        return {
            "error": f"Session {session_id} not found or expired",
            "category": "API_NOT_FOUND",
            "hint": "Create a new session with video_create_session",
        }

    try:
        if session.cache_name:
            result = await _continue_cached(session, prompt)
        else:
            result = await _continue_uncached(session, prompt)
        text, user_content = result

        model_content = types.Content(
            role="model",
            parts=[types.Part(text=text)],
        )
        turn = session_store.add_turn(session_id, user_content, model_content)
        from ..weaviate_store import store_session_turn
        await store_session_turn(session_id, session.video_title, turn, prompt, text)
        return SessionResponse(response=text, turn_count=turn).model_dump()
    except Exception as exc:
        return make_tool_error(exc)


async def _continue_uncached(
    session, prompt: str,
) -> tuple[str, types.Content]:
    """Continue a session by re-sending video file_data on every turn."""
    user_content = types.Content(
        role="user",
        parts=[
            types.Part(file_data=types.FileData(file_uri=session.url)),
            types.Part(text=prompt),
        ],
    )
    contents = list(session.history) + [user_content]

    client = GeminiClient.get()
    cfg = get_config()
    response = await with_retry(
        lambda: client.aio.models.generate_content(
            model=cfg.default_model,
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
            ),
        )
    )
    parts = response.candidates[0].content.parts if response.candidates else []
    text = "\n".join(p.text for p in parts if p.text and not getattr(p, "thought", False))
    return text, user_content


async def _continue_cached(
    session, prompt: str,
) -> tuple[str, types.Content]:
    """Continue a session using a Gemini context cache (text-only turns)."""
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )
    contents = list(session.history) + [user_content]

    try:
        client = GeminiClient.get()
        model = session.model or get_config().default_model
        response = await with_retry(
            lambda: client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="medium"),
                    cached_content=session.cache_name,
                ),
            )
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        text = "\n".join(p.text for p in parts if p.text and not getattr(p, "thought", False))

        asyncio.create_task(context_cache.refresh_ttl(session.cache_name))
        return text, user_content

    except Exception as exc:
        err_msg = str(exc).lower()
        if "not found" in err_msg or "expired" in err_msg or "cache" in err_msg:
            logger.warning(
                "Context cache %s expired/invalid, falling back to uncached path",
                session.cache_name,
            )
            session.cache_name = ""
            return await _continue_uncached(session, prompt)
        raise
