"""Video analysis models — structured output schemas for Gemini."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Timestamp(BaseModel):
    """A single timestamped moment in a video."""

    time: str = Field(default="", description="Precise timestamp in MM:SS or HH:MM:SS format")
    description: str = Field(default="", description="What is happening at this exact moment")


class VideoResult(BaseModel):
    """Default structured output for video_analyze.

    Used when the caller does not provide a custom ``output_schema``.
    All fields are optional (defaults) so Gemini can populate only what's relevant.
    """

    title: str = ""
    summary: str = ""
    key_points: list[str] = Field(
        default_factory=list,
        description="At least 5 substantive points with specific details from the video",
    )
    timestamps: list[Timestamp] = Field(
        default_factory=list,
        description="Precise timestamps (MM:SS) for key moments — not rounded estimates",
    )
    topics: list[str] = Field(default_factory=list)
    sentiment: str = ""


# ── Session models (unchanged — stateful, not structured-output) ────────────


class SessionInfo(BaseModel):
    """Returned when creating a video session."""

    session_id: str
    status: str = "created"
    video_title: str = ""
    source_type: str = ""


class SessionResponse(BaseModel):
    """Returned from continuing a video session."""

    response: str
    turn_count: int
