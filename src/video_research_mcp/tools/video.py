"""Video analysis tools — video_analyze and video_batch_analyze on a shared FastMCP sub-server."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from ..client import GeminiClient
from ..config import get_config
from ..errors import make_tool_error
from ..models.video_batch import BatchVideoItem, BatchVideoResult
from ..prompts.video import METADATA_OPTIMIZER, METADATA_PREAMBLE
from ..types import ThinkingLevel, VideoDirectoryPath, VideoFilePath, YouTubeUrl
from ..youtube import YouTubeClient
from .video_core import analyze_video
from .video_file import SUPPORTED_VIDEO_EXTENSIONS, _video_file_content
from .video_url import (
    _extract_video_id,
    _normalize_youtube_url,
    _video_content,
    _video_content_with_metadata,
)
from ._video_server import video_server

logger = logging.getLogger(__name__)

_SHORT_VIDEO_THRESHOLD = 5 * 60  # 5 minutes
_LONG_VIDEO_THRESHOLD = 30 * 60  # 30 minutes


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

        return await analyze_video(
            contents,
            instruction=instruction,
            content_id=content_id,
            source_label=source_label,
            output_schema=output_schema,
            thinking_level=thinking_level,
            use_cache=use_cache,
            metadata_context=metadata_context,
        )

    except (ValueError, FileNotFoundError) as exc:
        return make_tool_error(exc)
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


# Trigger session tool registration on shared video_server; re-export for backward compat
from .video_session import video_create_session, video_continue_session  # noqa: E402, F401
