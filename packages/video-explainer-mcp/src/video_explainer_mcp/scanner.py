"""Project directory inspector — reads filesystem, no CLI calls."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .config import get_config
from .models.project import ProjectInfo, ProjectListItem, StepStatus

logger = logging.getLogger(__name__)

# Step name → (directory, expected output pattern)
STEP_DETECTION: dict[str, tuple[str, str]] = {
    "input": ("input", ""),
    "script": ("script", "script.json"),
    "narration": ("narration", "narration.json"),
    "scenes": ("scenes", "scenes.json"),
    "voiceover": ("voiceover", ""),
    "storyboard": ("storyboard", ""),
}

PIPELINE_STEPS = ["script", "narration", "scenes", "voiceover", "storyboard"]


def _check_step(project_dir: Path, step_name: str) -> StepStatus:
    """Check if a pipeline step has been completed."""
    if step_name not in STEP_DETECTION:
        return StepStatus(name=step_name, completed=False)

    subdir_name, expected_file = STEP_DETECTION[step_name]
    step_dir = project_dir / subdir_name

    if not step_dir.is_dir():
        return StepStatus(name=step_name, completed=False)

    if expected_file:
        output = step_dir / expected_file
        return StepStatus(
            name=step_name,
            completed=output.is_file(),
            output_file=str(output) if output.is_file() else "",
        )

    # For steps without a specific expected file, check for any content
    has_files = any(step_dir.iterdir())
    return StepStatus(name=step_name, completed=has_files)


def _scan_project_sync(project_dir: Path) -> ProjectInfo:
    """Scan a single project directory for step completion (sync)."""
    steps = [_check_step(project_dir, s) for s in PIPELINE_STEPS]
    has_render = (project_dir / "output").is_dir() and any(
        f.suffix in {".mp4", ".webm"} for f in (project_dir / "output").iterdir()
    ) if (project_dir / "output").is_dir() else False
    has_short = (project_dir / "short" / "output").is_dir() if (project_dir / "short").is_dir() else False

    return ProjectInfo(
        project_id=project_dir.name,
        path=str(project_dir),
        steps=steps,
        has_render=has_render,
        has_short=has_short,
    )


def _list_projects_sync(projects_dir: Path) -> list[ProjectListItem]:
    """List all projects in the projects directory (sync)."""
    if not projects_dir.is_dir():
        return []

    items = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        info = _scan_project_sync(entry)
        completed = sum(1 for s in info.steps if s.completed)
        items.append(ProjectListItem(
            project_id=info.project_id,
            steps_completed=completed,
            steps_total=len(PIPELINE_STEPS),
            has_render=info.has_render,
        ))
    return items


async def scan_project(project_id: str) -> ProjectInfo | None:
    """Scan a project for step completion status.

    Args:
        project_id: The project identifier.

    Returns:
        ProjectInfo if the project directory exists, None otherwise.
    """
    cfg = get_config()
    project_dir = cfg.resolved_projects_path / project_id
    if not project_dir.is_dir():
        return None
    return await asyncio.to_thread(_scan_project_sync, project_dir)


def project_exists(project_id: str) -> bool:
    """Check if a project directory exists."""
    cfg = get_config()
    return (cfg.resolved_projects_path / project_id).is_dir()


async def list_projects() -> list[ProjectListItem]:
    """List all projects with their completion status.

    Returns:
        List of ProjectListItem summaries.
    """
    cfg = get_config()
    return await asyncio.to_thread(_list_projects_sync, cfg.resolved_projects_path)
