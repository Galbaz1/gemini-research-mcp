"""Weaviate collection definitions — 7 collections for knowledge storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyDef:
    """Single property in a Weaviate collection."""

    name: str
    data_type: list[str]
    description: str = ""
    skip_vectorization: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "dataType": self.data_type,
        }
        if self.description:
            result["description"] = self.description
        if self.skip_vectorization:
            result["moduleConfig"] = {
                "text2vec-weaviate": {"skip": True},
            }
        return result


@dataclass
class CollectionDef:
    """A Weaviate collection definition."""

    name: str
    description: str = ""
    properties: list[PropertyDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.name,
            "description": self.description,
            "properties": [p.to_dict() for p in self.properties],
        }


# ── Common properties (included in every collection) ───────────────────────

def _common_properties() -> list[PropertyDef]:
    return [
        PropertyDef("created_at", ["date"], "Timestamp of creation", skip_vectorization=True),
        PropertyDef("source_tool", ["text"], "Tool that generated this data", skip_vectorization=True),
    ]


# ── Collection definitions ──────────────────────────────────────────────────

RESEARCH_FINDINGS = CollectionDef(
    name="ResearchFindings",
    description="Research findings from research_deep and research_assess_evidence",
    properties=_common_properties() + [
        PropertyDef("topic", ["text"], "Research topic"),
        PropertyDef("scope", ["text"], "Research scope", skip_vectorization=True),
        PropertyDef("claim", ["text"], "Individual finding or claim"),
        PropertyDef("evidence_tier", ["text"], "Evidence tier label", skip_vectorization=True),
        PropertyDef("reasoning", ["text"], "Supporting reasoning"),
        PropertyDef("executive_summary", ["text"], "Report executive summary"),
        PropertyDef("confidence", ["number"], "Confidence score 0-1", skip_vectorization=True),
        PropertyDef("open_questions", ["text[]"], "Open research questions", skip_vectorization=True),
    ],
)

VIDEO_ANALYSES = CollectionDef(
    name="VideoAnalyses",
    description="Video analysis results from video_analyze and video_batch_analyze",
    properties=_common_properties() + [
        PropertyDef("video_id", ["text"], "YouTube video ID or file hash", skip_vectorization=True),
        PropertyDef("source_url", ["text"], "Source URL or file path", skip_vectorization=True),
        PropertyDef("instruction", ["text"], "Analysis instruction used"),
        PropertyDef("title", ["text"], "Video title"),
        PropertyDef("summary", ["text"], "Analysis summary"),
        PropertyDef("key_points", ["text[]"], "Key points extracted"),
        PropertyDef("raw_result", ["text"], "Full JSON result", skip_vectorization=True),
    ],
)

CONTENT_ANALYSES = CollectionDef(
    name="ContentAnalyses",
    description="Content analysis results from content_analyze",
    properties=_common_properties() + [
        PropertyDef("source", ["text"], "Source URL, file path, or '(text)'", skip_vectorization=True),
        PropertyDef("instruction", ["text"], "Analysis instruction used"),
        PropertyDef("title", ["text"], "Content title"),
        PropertyDef("summary", ["text"], "Analysis summary"),
        PropertyDef("key_points", ["text[]"], "Key points extracted"),
        PropertyDef("entities", ["text[]"], "Named entities found"),
        PropertyDef("raw_result", ["text"], "Full JSON result", skip_vectorization=True),
    ],
)

VIDEO_METADATA = CollectionDef(
    name="VideoMetadata",
    description="YouTube video metadata from video_metadata",
    properties=_common_properties() + [
        PropertyDef("video_id", ["text"], "YouTube video ID", skip_vectorization=True),
        PropertyDef("title", ["text"], "Video title"),
        PropertyDef("description", ["text"], "Video description"),
        PropertyDef("channel_title", ["text"], "Channel name"),
        PropertyDef("tags", ["text[]"], "Video tags"),
        PropertyDef("view_count", ["int"], "View count", skip_vectorization=True),
        PropertyDef("like_count", ["int"], "Like count", skip_vectorization=True),
        PropertyDef("duration", ["text"], "Video duration", skip_vectorization=True),
        PropertyDef("published_at", ["text"], "Publish date", skip_vectorization=True),
    ],
)

SESSION_TRANSCRIPTS = CollectionDef(
    name="SessionTranscripts",
    description="Session turns from video_continue_session",
    properties=_common_properties() + [
        PropertyDef("session_id", ["text"], "Session ID", skip_vectorization=True),
        PropertyDef("video_title", ["text"], "Video title for this session"),
        PropertyDef("turn_index", ["int"], "Turn number in session", skip_vectorization=True),
        PropertyDef("turn_prompt", ["text"], "User prompt for this turn"),
        PropertyDef("turn_response", ["text"], "Model response for this turn"),
    ],
)

WEB_SEARCH_RESULTS = CollectionDef(
    name="WebSearchResults",
    description="Web search results from web_search",
    properties=_common_properties() + [
        PropertyDef("query", ["text"], "Search query"),
        PropertyDef("response", ["text"], "Search response text"),
        PropertyDef("sources_json", ["text"], "Grounding sources as JSON", skip_vectorization=True),
    ],
)

RESEARCH_PLANS = CollectionDef(
    name="ResearchPlans",
    description="Research orchestration plans from research_plan",
    properties=_common_properties() + [
        PropertyDef("topic", ["text"], "Research topic"),
        PropertyDef("scope", ["text"], "Research scope", skip_vectorization=True),
        PropertyDef("task_decomposition", ["text[]"], "Task breakdown"),
        PropertyDef("phases_json", ["text"], "Phases as JSON", skip_vectorization=True),
    ],
)


ALL_COLLECTIONS: list[CollectionDef] = [
    RESEARCH_FINDINGS,
    VIDEO_ANALYSES,
    CONTENT_ANALYSES,
    VIDEO_METADATA,
    SESSION_TRANSCRIPTS,
    WEB_SEARCH_RESULTS,
    RESEARCH_PLANS,
]
