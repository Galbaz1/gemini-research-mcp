"""Shared type aliases for tool parameters."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

# ── Literal enums ────────────────────────────────────────────────────────────

ThinkingLevel = Literal["minimal", "low", "medium", "high"]
Scope = Literal["quick", "moderate", "deep", "comprehensive"]
CacheAction = Literal["stats", "list", "clear"]

# ── Annotated aliases ────────────────────────────────────────────────────────

YouTubeUrl = Annotated[str, Field(min_length=10, description="YouTube video URL (youtube.com or youtu.be)")]
TopicParam = Annotated[str, Field(min_length=3, max_length=500, description="Research topic or question")]
