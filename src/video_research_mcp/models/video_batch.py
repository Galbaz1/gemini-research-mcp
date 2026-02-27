"""Batch video analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BatchVideoItem(BaseModel):
    """Result for a single file in a batch analysis."""

    file_name: str
    file_path: str
    result: dict = Field(default_factory=dict)
    error: str = ""


class BatchVideoResult(BaseModel):
    """Aggregated result from video_batch_analyze."""

    directory: str
    total_files: int
    successful: int
    failed: int
    items: list[BatchVideoItem] = Field(default_factory=list)
