"""Shared type aliases for tool parameters."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

# ── Literal enums ────────────────────────────────────────────────────────────

ThinkingLevel = Literal["minimal", "low", "medium", "high"]
Scope = Literal["quick", "moderate", "deep", "comprehensive"]
CacheAction = Literal["stats", "list", "clear"]
ModelPreset = Literal["best", "stable", "budget"]
KnowledgeCollection = Literal[
    "ResearchFindings", "VideoAnalyses", "ContentAnalyses",
    "VideoMetadata", "SessionTranscripts", "WebSearchResults", "ResearchPlans",
    "CommunityReactions", "ConceptKnowledge", "RelationshipEdges", "CallNotes",
]

# ── Annotated aliases ────────────────────────────────────────────────────────

YouTubeUrl = Annotated[str, Field(min_length=10, description="YouTube video URL (youtube.com or youtu.be)")]
TopicParam = Annotated[str, Field(min_length=3, max_length=500, description="Research topic or question")]
VideoFilePath = Annotated[str, Field(
    min_length=1,
    description="Path to a local video file (mp4, webm, mov, avi, mkv, mpeg, wmv, 3gpp)",
)]
VideoDirectoryPath = Annotated[str, Field(
    min_length=1,
    description="Path to a directory containing video files",
)]
PlaylistUrl = Annotated[str, Field(
    min_length=10,
    description="YouTube playlist URL (must contain 'list=' parameter)",
)]
