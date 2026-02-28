"""Pipeline execution result models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StepResult(BaseModel):
    """Result of running a single pipeline step."""

    project_id: str
    step: str
    success: bool
    output_file: str = ""
    duration_seconds: float = 0.0
    message: str = ""


class RenderResult(BaseModel):
    """Result of a video render operation."""

    project_id: str
    success: bool
    output_file: str = ""
    duration_seconds: float = 0.0
    resolution: str = ""
    message: str = ""


class InjectResult(BaseModel):
    """Result of injecting content into a project."""

    project_id: str
    files_written: list[str] = Field(default_factory=list)
    message: str = ""
