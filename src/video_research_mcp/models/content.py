"""Content analysis models — structured output schemas for Gemini."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContentResult(BaseModel):
    """Default structured output for content_analyze.

    Replaces the old ``DocumentAnalysis`` and ``Summary`` models.
    Used when the caller does not provide a custom ``output_schema``.
    """

    title: str = ""
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    structure_notes: str = ""
    quality_assessment: str = ""
