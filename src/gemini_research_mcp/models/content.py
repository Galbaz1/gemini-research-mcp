"""Content analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentAnalysis(BaseModel):
    """Result of analysing a document or URL."""

    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    structure: str = ""
    entities: list[str] = Field(default_factory=list)
    methodology_notes: str = ""
    quality_assessment: str = ""


class Summary(BaseModel):
    """Condensed summary output."""

    text: str = ""
    word_count: int = 0
    key_takeaways: list[str] = Field(default_factory=list)
