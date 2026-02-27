"""Video analysis tools — 4 tools on a FastMCP sub-server."""

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
from ..config import get_config
from ..errors import make_tool_error
from ..models.video import SessionInfo, SessionResponse
from ..models.video_batch import BatchVideoItem, BatchVideoResult
from ..sessions import session_store
from ..types import ThinkingLevel, VideoDirectoryPath, VideoFilePath, YouTubeUrl
from ..youtube import YouTubeClient
from .video_core import analyze_video
from .video_file import (
    SUPPORTED_VIDEO_EXTENSIONS,
    _video_file_content,
    _video_file_uri,
)
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
        if url:
            clean_url = _normalize_youtube_url(url)
            content_id = _extract_video_id(url)
            contents = _video_content(clean_url, instruction)
            source_label = clean_url
        else:
            contents, content_id = await _video_file_content(file_path, instruction)
            source_label = file_path

        return await analyze_video(
            contents,
            instruction=instruction,
            content_id=content_id,
            source_label=source_label,
            output_schema=output_schema,
            thinking_level=thinking_level,
            use_cache=use_cache,
        )

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

    session = session_store.create(clean_url, "general", video_title=title)
    return SessionInfo(
        session_id=session.session_id,
        status="created",
        video_title=title,
        source_type=source_type,
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


@video_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def video_batch_analyze(
    directory: VideoDirectoryPath,
    instruction: Annotated[str, Field(
        description="What to analyze in each video"
    )] = "Provide a comprehensive analysis of this video.",
    glob_pattern: Annotated[str, Field(
        description="Glob pattern to filter files within the directory"
    )] = "*",
    output_schema: Annotated[dict | None, Field(
        description="Optional JSON Schema for each video's response"
    )] = None,
    thinking_level: ThinkingLevel = "high",
    max_files: Annotated[int, Field(ge=1, le=50, description="Maximum files to process")] = 20,
) -> dict:
    """Analyze all video files in a directory concurrently.

    Scans the directory for supported video files (mp4, webm, mov, avi, mkv,
    mpeg, wmv, 3gpp), then analyzes each with the given instruction using
    bounded concurrency (3 parallel Gemini calls).

    Args:
        directory: Path to a directory containing video files.
        instruction: What to analyze in each video.
        glob_pattern: Glob to filter files (default "*" matches all).
        output_schema: Optional JSON Schema dict for each result.
        thinking_level: Gemini thinking depth.
        max_files: Maximum number of files to process.

    Returns:
        Dict with directory, counts, and per-file results.
    """
    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.is_dir():
        return make_tool_error(ValueError(f"Not a directory: {directory}"))

    video_files = sorted(
        f for f in dir_path.glob(glob_pattern)
        if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    )[:max_files]

    if not video_files:
        return BatchVideoResult(
            directory=str(dir_path),
            total_files=0,
            successful=0,
            failed=0,
        ).model_dump()

    semaphore = asyncio.Semaphore(3)

    async def _process(fp: Path) -> BatchVideoItem:
        async with semaphore:
            try:
                contents, content_id = await _video_file_content(str(fp), instruction)
                result = await analyze_video(
                    contents,
                    instruction=instruction,
                    content_id=content_id,
                    source_label=str(fp),
                    output_schema=output_schema,
                    thinking_level=thinking_level,
                    use_cache=True,
                )
                return BatchVideoItem(file_name=fp.name, file_path=str(fp), result=result)
            except Exception as exc:
                return BatchVideoItem(file_name=fp.name, file_path=str(fp), error=str(exc))

    items = await asyncio.gather(*[_process(f) for f in video_files])
    successful = sum(1 for i in items if not i.error)
    return BatchVideoResult(
        directory=str(dir_path),
        total_files=len(items),
        successful=successful,
        failed=len(items) - successful,
        items=list(items),
    ).model_dump()
