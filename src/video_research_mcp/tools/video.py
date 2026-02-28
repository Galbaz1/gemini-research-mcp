"""Video analysis tools — 3 single-video tools on a FastMCP sub-server.

Batch analysis lives in video_batch.py, registered via side-effect import.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from google.genai import types
from mcp.types import ToolAnnotations
from pydantic import Field

from ..client import GeminiClient
from ..retry import with_retry
from ..config import get_config
from ..errors import make_tool_error
from ..models.video import SessionInfo, SessionResponse
from ..prompts.video import METADATA_OPTIMIZER, METADATA_PREAMBLE
from ..sessions import session_store
from ..types import ThinkingLevel, VideoFilePath, YouTubeUrl
from ..youtube import YouTubeClient
from .video_core import analyze_video
from .video_file import _video_file_content, _video_file_uri
from .. import context_cache
from .video_url import (
    _extract_video_id,
    _normalize_youtube_url,
    _video_content,
    _video_content_with_metadata,
)

logger = logging.getLogger(__name__)
video_server = FastMCP("video")

_SHORT_VIDEO_THRESHOLD = 5 * 60  # 5 minutes
_LONG_VIDEO_THRESHOLD = 30 * 60  # 30 minutes
_background_tasks: set[asyncio.Task] = set()  # prevent GC of fire-and-forget tasks


async def _youtube_metadata_pipeline(
    video_id: str, instruction: str
) -> tuple[str | None, float | None]:
    """Fetch YouTube metadata and build analysis context + fps override.

    Non-fatal: returns (None, None) on any failure so the caller falls back
    to the generic pipeline.

    Returns:
        (metadata_context, fps_override) — context string for the analysis
        prompt and optional fps sampling rate.
    """
    try:
        meta = await YouTubeClient.video_metadata(video_id)
        if not meta.title:
            return None, None
    except Exception:
        logger.debug("YouTube metadata fetch failed for %s", video_id)
        return None, None

    fps_override: float | None = None
    if meta.duration_seconds > 0:
        if meta.duration_seconds < _SHORT_VIDEO_THRESHOLD:
            fps_override = 2.0
        elif meta.duration_seconds > _LONG_VIDEO_THRESHOLD:
            fps_override = 1.0

    tags_str = ", ".join(meta.tags[:10]) if meta.tags else "none"
    desc_excerpt = (meta.description[:200] + "...") if len(meta.description) > 200 else meta.description

    preamble = METADATA_PREAMBLE.format(
        title=meta.title,
        channel=meta.channel_title,
        category=meta.category or "Unknown",
        duration=meta.duration_display,
        tags=tags_str,
    )

    try:
        cfg = get_config()
        optimizer_prompt = METADATA_OPTIMIZER.format(
            title=meta.title,
            channel=meta.channel_title,
            category=meta.category or "Unknown",
            duration=meta.duration_display,
            description_excerpt=desc_excerpt,
            tags=tags_str,
            instruction=instruction,
        )
        optimized = await GeminiClient.generate(
            optimizer_prompt, model=cfg.flash_model, thinking_level="low"
        )
        context = f"{preamble}\n\nOptimized extraction focus: {optimized.strip()}"
    except Exception:
        logger.debug("Flash optimizer failed, using preamble only")
        context = preamble

    return context, fps_override


@video_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def video_analyze(
    url: YouTubeUrl | None = None,
    file_path: VideoFilePath | None = None,
    instruction: Annotated[str, Field(
        description="What to analyze — e.g. 'summarize key points', "
        "'extract all CLI commands shown', 'list all recipes and ingredients'"
    )] = "Provide a comprehensive analysis of this video.",
    output_schema: Annotated[dict | None, Field(
        description="Optional JSON Schema for the response. "
        "If omitted, uses default VideoResult schema."
    )] = None,
    thinking_level: ThinkingLevel = "high",
    use_cache: Annotated[bool, Field(description="Use cached results")] = True,
) -> dict:
    """Analyze a video (YouTube URL or local file) with any instruction.

    Provide exactly one of url or file_path. Uses Gemini's structured output
    for reliable JSON responses. Pass a custom output_schema to control the
    response shape, or use the default VideoResult schema.

    Args:
        url: YouTube video URL.
        file_path: Path to a local video file.
        instruction: What to analyze or extract from the video.
        output_schema: Optional JSON Schema dict for custom output shape.
        thinking_level: Gemini thinking depth.
        use_cache: Whether to use cached results.

    Returns:
        Dict matching VideoResult schema (default) or the custom output_schema.
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
        metadata_context = None
        if url:
            clean_url = _normalize_youtube_url(url)
            content_id = _extract_video_id(url)
            source_label = clean_url

            meta_ctx, fps_override = await _youtube_metadata_pipeline(
                content_id, instruction
            )
            if meta_ctx:
                metadata_context = meta_ctx
                contents = _video_content_with_metadata(
                    clean_url, instruction, fps=fps_override
                )
            else:
                contents = _video_content(clean_url, instruction)
        else:
            contents, content_id = await _video_file_content(file_path, instruction)
            source_label = file_path

        result = await analyze_video(
            contents,
            instruction=instruction,
            content_id=content_id,
            source_label=source_label,
            output_schema=output_schema,
            thinking_level=thinking_level,
            use_cache=use_cache,
            metadata_context=metadata_context,
        )

        # Pre-warm context cache for future session reuse (YouTube only)
        if url and content_id:
            cfg = get_config()
            warm_parts = [types.Part(file_data=types.FileData(file_uri=clean_url))]
            task = asyncio.create_task(
                context_cache.get_or_create(content_id, warm_parts, cfg.default_model)
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

        return result

    except (ValueError, FileNotFoundError) as exc:
        return make_tool_error(exc)
    except Exception as exc:
        return make_tool_error(exc)


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
        else:
            uri, _ = await _video_file_uri(file_path)
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

    # Look up pre-warmed context cache (YouTube only)
    cache_name = ""
    cache_model = ""
    if source_type == "youtube":
        try:
            vid = _extract_video_id(url)
            cfg = get_config()
            cache_name = context_cache.lookup(vid, cfg.default_model) or ""
            if cache_name:
                cache_model = cfg.default_model
        except Exception:
            pass

    session = session_store.create(
        clean_url, "general",
        video_title=title,
        cache_name=cache_name,
        model=cache_model,
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

    # When cached content is available, omit the video Part from user messages
    # (the video is already in the Gemini cache prefix).
    # If TTL refresh fails, the cache is likely expired — fall back to inline video.
    use_cache = False
    if session.cache_name:
        cache_alive = await context_cache.refresh_ttl(session.cache_name)
        if cache_alive:
            use_cache = True
        else:
            session.cache_name = ""

    if use_cache:
        user_parts = [types.Part(text=prompt)]
    else:
        user_parts = [
            types.Part(file_data=types.FileData(file_uri=session.url)),
            types.Part(text=prompt),
        ]
    user_content = types.Content(role="user", parts=user_parts)
    contents = list(session.history) + [user_content]

    try:
        client = GeminiClient.get()
        cfg = get_config()

        config_kwargs: dict = {
            "thinking_config": types.ThinkingConfig(thinking_level="medium"),
        }
        if use_cache:
            config_kwargs["cached_content"] = session.cache_name

        # Use the model the cache was created for, or default
        model = session.model if use_cache and session.model else cfg.default_model
        response = await with_retry(
            lambda: client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        text = "\n".join(p.text for p in parts if p.text and not getattr(p, "thought", False))

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


# Register batch tool on video_server (side-effect import + re-export)
from .video_batch import video_batch_analyze  # noqa: F401, E402
