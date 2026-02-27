"""Video analysis models — structured output schemas for Gemini."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Timestamp(BaseModel):
    """A single timestamped moment in a video."""

    time: str = ""
    description: str = ""


class VideoResult(BaseModel):
    """Default structured output for video_analyze.

    Used when the caller does not provide a custom ``output_schema``.
    All fields are optional (defaults) so Gemini can populate only what's relevant.
    """

    title: str = ""
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    timestamps: list[Timestamp] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    sentiment: str = ""


# ── Session models (unchanged — stateful, not structured-output) ────────────


class SessionInfo(BaseModel):
    """Returned when creating a video session."""

    session_id: str
    status: str = "created"
    video_title: str = ""


class SessionResponse(BaseModel):
    """Returned from continuing a video session."""

    response: str
    turn_count: int
