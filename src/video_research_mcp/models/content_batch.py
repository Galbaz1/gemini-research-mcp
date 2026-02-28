"""Batch content analysis models — output schemas for content_batch_analyze.

BatchContentResult aggregates per-file results from scanning a directory
or explicit file list. Files are either compared in a single Gemini call
(compare mode) or analyzed individually with bounded concurrency.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BatchContentItem(BaseModel):
    """Result for a single file in a batch content analysis."""

    file_name: str
    file_path: str
    result: dict = Field(default_factory=dict)
    error: str = ""


class BatchContentResult(BaseModel):
    """Output schema for content_batch_analyze.

    Returned directly by the tool — not used with generate_structured since
    results are aggregated locally from individual or comparative analysis.
    """

    directory: str = ""
    total_files: int
    successful: int
    failed: int
    mode: str = "compare"
    items: list[BatchContentItem] = Field(default_factory=list)
    comparison: dict = Field(default_factory=dict)
