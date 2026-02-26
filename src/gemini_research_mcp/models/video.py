"""Video analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VideoAnalysis(BaseModel):
    """Result of analysing a single YouTube video."""

    url: str
    mode: str = "general"
    title: str = ""
    summary: str = ""
    key_moments: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sentiment: str = ""
    # Tutorial / claude_code mode fields
    commands: list[str] = Field(default_factory=list)
    code_snippets: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    tools_mentioned: list[str] = Field(default_factory=list)
    # Error fields
    error: str | None = None
    error_category: str | None = None
    error_hint: str | None = None
    cached: bool = False


class ComparisonResult(BaseModel):
    """Cross-video comparison output."""

    common_themes: list[str] = Field(default_factory=list)
    common_commands: list[str] = Field(default_factory=list)
    unique_per_video: dict[str, list[str]] = Field(default_factory=dict)
    recommendation: str = ""


class SessionInfo(BaseModel):
    """Returned when creating a video session."""

    session_id: str
    status: str = "created"
    video_title: str = ""


class SessionResponse(BaseModel):
    """Returned from continuing a video session."""

    response: str
    turn_count: int
