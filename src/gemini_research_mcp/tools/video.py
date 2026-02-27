"""Video analysis tools — 3 tools on a FastMCP sub-server."""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastmcp import FastMCP
from google.genai import types
from mcp.types import ToolAnnotations
from pydantic import Field

from ..cache import load as cache_load, save as cache_save
from ..client import GeminiClient
from ..config import get_config
from ..errors import make_tool_error
from ..models.video import SessionInfo, SessionResponse, VideoResult
from ..sessions import session_store
from ..types import ThinkingLevel, YouTubeUrl
from .video_url import _extract_video_id, _normalize_youtube_url, _video_content

logger = logging.getLogger(__name__)
video_server = FastMCP("video")


@video_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def video_analyze(
    url: YouTubeUrl,
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
    """Analyze a YouTube video with any instruction.

    Uses Gemini's structured output for reliable JSON responses.
    Pass a custom output_schema to control the response shape,
    or use the default VideoResult schema.

    Args:
        url: YouTube video URL.
        instruction: What to analyze or extract from the video.
        output_schema: Optional JSON Schema dict for custom output shape.
        thinking_level: Gemini thinking depth.
        use_cache: Whether to use cached results.

    Returns:
        Dict matching VideoResult schema (default) or the custom output_schema.
    """
    try:
        clean_url = _normalize_youtube_url(url)
        video_id = _extract_video_id(url)
    except ValueError as exc:
        return make_tool_error(exc)

    cfg = get_config()

    if use_cache:
        cached = cache_load(video_id, "video_analyze", cfg.default_model, instruction=instruction)
        if cached:
            cached["cached"] = True
            return cached

    try:
        contents = _video_content(clean_url, instruction)

        if output_schema:
            raw = await GeminiClient.generate(
                contents,
                thinking_level=thinking_level,
                response_schema=output_schema,
            )
            result = json.loads(raw)
        else:
            model_result = await GeminiClient.generate_structured(
                contents,
                schema=VideoResult,
                thinking_level=thinking_level,
            )
            result = model_result.model_dump()

        result["url"] = clean_url
        if use_cache:
            cache_save(video_id, "video_analyze", cfg.default_model, result, instruction=instruction)
        return result

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
    url: YouTubeUrl,
    description: Annotated[str, Field(description="Session purpose or focus area")] = "",
) -> dict:
    """Create a persistent session for multi-turn video exploration.

    Args:
        url: YouTube video URL.
        description: Optional focus area for the session.

    Returns:
        Dict with session_id, status, and video_title.
    """
    try:
        clean_url = _normalize_youtube_url(url)
    except ValueError as exc:
        return make_tool_error(exc)

    try:
        resp = await GeminiClient.generate(
            _video_content(clean_url, "What is the title of this video? Reply with just the title."),
            thinking_level="low",
        )
        title = resp.strip()
    except Exception:
        title = ""

    session = session_store.create(clean_url, "general", video_title=title)
    return SessionInfo(
        session_id=session.session_id,
        status="created",
        video_title=title,
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

    user_content = types.Content(
        role="user",
        parts=[
            types.Part(file_data=types.FileData(file_uri=session.url)),
            types.Part(text=prompt),
        ],
    )
    contents = list(session.history) + [user_content]

    try:
        client = GeminiClient.get()
        cfg = get_config()
        response = await client.aio.models.generate_content(
            model=cfg.default_model,
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
            ),
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        text = "\n".join(p.text for p in parts if p.text and not getattr(p, "thought", False))

        model_content = types.Content(
            role="model",
            parts=[types.Part(text=text)],
        )
        turn = session_store.add_turn(session_id, user_content, model_content)
        return SessionResponse(response=text, turn_count=turn).model_dump()
    except Exception as exc:
        return make_tool_error(exc)
