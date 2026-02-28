"""Pipeline execution tools — generate, step, render, shorts."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from ..config import get_config
from ..errors import make_tool_error
from ..jobs import JobStatus, create_job, get_job, update_job
from ..models.pipeline import RenderResult, StepResult
from ..runner import run_cli
from ..types import PipelineStep, ProjectId, RenderResolution

logger = logging.getLogger(__name__)
pipeline_server = FastMCP("pipeline")

# Prevent background render tasks from being garbage-collected mid-execution.
# See: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_background_tasks: set[asyncio.Task] = set()


def _tts_args() -> list[str]:
    """Build TTS-related CLI arguments from config."""
    cfg = get_config()
    args: list[str] = []
    if cfg.tts_provider != "mock":
        args.extend(["--tts-provider", cfg.tts_provider])
    else:
        args.append("--mock")
    return args


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False))
async def explainer_generate(
    project_id: ProjectId,
    from_step: Annotated[str | None, Field(description="Start from this step")] = None,
    to_step: Annotated[str | None, Field(description="Stop after this step")] = None,
    force: Annotated[bool, Field(description="Re-run already completed steps")] = False,
) -> dict:
    """Run the full explainer pipeline (or a subset of steps).

    Args:
        project_id: Target project.
        from_step: Start from this pipeline step (skip earlier steps).
        to_step: Stop after this step (skip later steps).
        force: Re-run steps even if already completed.

    Returns:
        Dict with project_id, success status, duration, and CLI output.
    """
    try:
        args = ["generate", project_id]
        if from_step:
            args.extend(["--from", from_step])
        if to_step:
            args.extend(["--to", to_step])
        if force:
            args.append("--force")
        args.extend(_tts_args())

        result = await run_cli(*args)
        return {
            "project_id": project_id,
            "success": True,
            "duration_seconds": result.duration_seconds,
            "stdout": result.stdout.strip(),
        }
    except Exception as exc:
        return make_tool_error(exc)


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False))
async def explainer_step(
    project_id: ProjectId,
    step: Annotated[PipelineStep, Field(description="Pipeline step to run")],
) -> dict:
    """Run a single pipeline step.

    Args:
        project_id: Target project.
        step: One of: script, narration, scenes, voiceover, storyboard.

    Returns:
        StepResult with success status and output file.
    """
    try:
        args = [step, project_id]
        args.extend(_tts_args())

        result = await run_cli(*args)
        return StepResult(
            project_id=project_id,
            step=step,
            success=True,
            duration_seconds=result.duration_seconds,
            message=result.stdout.strip(),
        ).model_dump()
    except Exception as exc:
        return make_tool_error(exc)


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False))
async def explainer_render(
    project_id: ProjectId,
    resolution: Annotated[RenderResolution, Field(description="Output resolution")] = "720p",
    fast: Annotated[bool, Field(description="Use fast/preview quality")] = True,
) -> dict:
    """Render the explainer video (blocking — waits for completion).

    For long renders, prefer ``explainer_render_start`` + ``explainer_render_poll``.

    Args:
        project_id: Project with completed pipeline steps.
        resolution: Video resolution preset.
        fast: Use fast/preview quality for quicker renders.

    Returns:
        RenderResult with output file path and duration.
    """
    try:
        cfg = get_config()
        args = ["render", project_id, "-r", resolution]
        if fast:
            args.append("--fast")

        result = await run_cli(*args, timeout=cfg.render_timeout)
        output_dir = cfg.resolved_projects_path / project_id / "output"
        output_file = ""
        if output_dir.is_dir():
            for f in output_dir.iterdir():
                if f.suffix in {".mp4", ".webm"}:
                    output_file = str(f)
                    break

        return RenderResult(
            project_id=project_id,
            success=True,
            output_file=output_file,
            duration_seconds=result.duration_seconds,
            resolution=resolution,
            message="Render complete",
        ).model_dump()
    except Exception as exc:
        return make_tool_error(exc)


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False))
async def explainer_render_start(
    project_id: ProjectId,
    resolution: Annotated[RenderResolution, Field(description="Output resolution")] = "720p",
    fast: Annotated[bool, Field(description="Use fast/preview quality")] = True,
) -> dict:
    """Start a background render and return immediately with a job ID.

    Poll progress with ``explainer_render_poll``.

    Args:
        project_id: Project to render.
        resolution: Video resolution preset.
        fast: Use fast/preview quality.

    Returns:
        Dict with job_id for polling.
    """
    try:
        job = create_job(project_id)
        update_job(job.job_id, status=JobStatus.RUNNING)

        async def _render_background():
            start = time.monotonic()
            try:
                cfg = get_config()
                args = ["render", project_id, "-r", resolution]
                if fast:
                    args.append("--fast")
                await run_cli(*args, timeout=cfg.render_timeout)

                output_file = ""
                output_dir = cfg.resolved_projects_path / project_id / "output"
                if output_dir.is_dir():
                    for f in output_dir.iterdir():
                        if f.suffix in {".mp4", ".webm"}:
                            output_file = str(f)
                            break

                update_job(
                    job.job_id,
                    status=JobStatus.COMPLETED,
                    output_file=output_file,
                    duration_seconds=round(time.monotonic() - start, 2),
                )
            except Exception as exc:
                update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    error=str(exc),
                    duration_seconds=round(time.monotonic() - start, 2),
                )

        task = asyncio.create_task(_render_background())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        return {
            "job_id": job.job_id,
            "project_id": project_id,
            "status": "running",
            "message": "Render started in background — poll with explainer_render_poll",
        }
    except Exception as exc:
        return make_tool_error(exc)


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
async def explainer_render_poll(
    job_id: Annotated[str, Field(description="Job ID from explainer_render_start")],
) -> dict:
    """Check the status of a background render job.

    Args:
        job_id: The 12-char hex job identifier.

    Returns:
        Dict with current job status, output file (if complete), or error.
    """
    try:
        job = get_job(job_id)
        if job is None:
            return make_tool_error(
                KeyError(f"Job not found: {job_id}")
            )
        return {
            "job_id": job.job_id,
            "project_id": job.project_id,
            "status": job.status.value,
            "output_file": job.output_file,
            "error": job.error,
            "duration_seconds": job.duration_seconds,
            "started_at": job.started_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    except Exception as exc:
        return make_tool_error(exc)


@pipeline_server.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False))
async def explainer_short(
    project_id: ProjectId,
) -> dict:
    """Generate a short-form video from an existing project.

    Args:
        project_id: Project with completed pipeline.

    Returns:
        Dict with success status and output info.
    """
    try:
        args = ["short", "generate", project_id]
        args.extend(_tts_args())
        result = await run_cli(*args)
        return {
            "project_id": project_id,
            "success": True,
            "duration_seconds": result.duration_seconds,
            "stdout": result.stdout.strip(),
        }
    except Exception as exc:
        return make_tool_error(exc)
