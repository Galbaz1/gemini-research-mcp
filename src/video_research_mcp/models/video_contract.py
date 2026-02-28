"""Strict video analysis models — enforced constraints for contract mode.

Used by the strict pipeline (contract/) to guarantee minimum quality:
tight min_length/min_items constraints force Gemini to produce substantive
output that passes quality gates.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StrictTimestamp(BaseModel):
    """A timestamped moment with enforced non-empty fields."""

    time: str = Field(min_length=3, description="Timestamp in MM:SS or HH:MM:SS format")
    description: str = Field(min_length=10, description="What is happening at this moment")


class StrictVideoResult(BaseModel):
    """Strict structured output for video_analyze with contract enforcement.

    All fields have minimum constraints so Gemini cannot return empty/shallow results.
    """

    title: str = Field(min_length=1, description="Video title")
    summary: str = Field(min_length=50, description="Comprehensive summary of the video content")
    key_points: list[str] = Field(
        min_length=3,
        description="Substantive points with specific details from the video",
    )
    timestamps: list[StrictTimestamp] = Field(
        min_length=3,
        description="Precise timestamps for key moments in MM:SS format",
    )
    topics: list[str] = Field(
        min_length=1,
        description="Topics covered in the video",
    )
    sentiment: str = Field(min_length=1, description="Overall sentiment or tone")
    duration_seconds: int = Field(default=0, ge=0, description="Video duration in seconds")


class StrategySection(BaseModel):
    """A section of the strategy report."""

    heading: str = Field(min_length=1, description="Section heading")
    content: str = Field(min_length=20, description="Section content with analysis")


class StrategyReport(BaseModel):
    """Strategic analysis derived from video content."""

    title: str = Field(min_length=1, description="Report title")
    sections: list[StrategySection] = Field(
        min_length=1, description="Report sections with strategic analysis"
    )
    strategic_notes: list[str] = Field(
        min_length=1, description="Key strategic takeaways"
    )


class ConceptMapNode(BaseModel):
    """A node in the concept map."""

    id: str = Field(min_length=1, description="Unique node identifier")
    label: str = Field(min_length=1, description="Display label")
    category: str = Field(default="general", description="Node category for grouping")


class ConceptMapEdge(BaseModel):
    """A directed edge between concept map nodes."""

    source: str = Field(min_length=1, description="Source node id")
    target: str = Field(min_length=1, description="Target node id")
    label: str = Field(default="", description="Edge label describing the relationship")


class ConceptMap(BaseModel):
    """A concept map with nodes and edges."""

    nodes: list[ConceptMapNode] = Field(
        min_length=2, description="Concept nodes"
    )
    edges: list[ConceptMapEdge] = Field(
        min_length=1, description="Relationships between concepts"
    )


class QualityCheck(BaseModel):
    """A single quality gate result."""

    name: str
    passed: bool
    detail: str = ""


class QualityReport(BaseModel):
    """Aggregated quality gate results."""

    status: str = Field(description="'pass' or 'fail'")
    coverage_ratio: float = Field(ge=0.0, le=1.0, description="Video coverage ratio")
    checks: list[QualityCheck] = Field(default_factory=list)
    duration_seconds: float = Field(default=0.0, ge=0.0)
