"""Project-level data models for explainer status and listing."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StepStatus(BaseModel):
    """Completion status for a single pipeline step."""

    name: str
    completed: bool = False
    output_file: str = ""


class ProjectInfo(BaseModel):
    """Full project status with step-by-step completion."""

    project_id: str
    path: str
    steps: list[StepStatus] = Field(default_factory=list)
    has_render: bool = False
    has_short: bool = False


class ProjectListItem(BaseModel):
    """Summary entry for project listing."""

    project_id: str
    steps_completed: int = 0
    steps_total: int = 5
    has_render: bool = False
