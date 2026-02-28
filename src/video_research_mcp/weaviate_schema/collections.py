"""Original 7 Weaviate collection definitions.

These collections were part of the initial storage schema:
ResearchFindings, VideoAnalyses, ContentAnalyses, VideoMetadata,
SessionTranscripts, WebSearchResults, ResearchPlans.
"""

from __future__ import annotations

from .base import CollectionDef, PropertyDef, ReferenceDef, _common_properties


RESEARCH_FINDINGS = CollectionDef(
    name="ResearchFindings",
    description="Research findings from research_deep and research_assess_evidence",
    properties=_common_properties() + [
        PropertyDef("topic", ["text"], "Research topic"),
        PropertyDef("scope", ["text"], "Research scope", skip_vectorization=True, index_searchable=False),
        PropertyDef("claim", ["text"], "Individual finding or claim"),
        PropertyDef(
            "evidence_tier", ["text"], "Evidence tier label",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("reasoning", ["text"], "Supporting reasoning"),
        PropertyDef("executive_summary", ["text"], "Report executive summary"),
        PropertyDef(
            "confidence", ["number"], "Confidence score 0-1",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef("open_questions", ["text[]"], "Open research questions", skip_vectorization=True),
        PropertyDef("supporting", ["text[]"], "Supporting evidence sources"),
        PropertyDef("contradicting", ["text[]"], "Contradicting evidence sources"),
        PropertyDef("methodology_critique", ["text"], "Critique of research methodology"),
        PropertyDef("recommendations", ["text[]"], "Action recommendations"),
        PropertyDef(
            "report_uuid", ["text"], "Parent report UUID",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
    references=[
        ReferenceDef("belongs_to_report", "ResearchFindings", "Link to parent report"),
    ],
)

VIDEO_ANALYSES = CollectionDef(
    name="VideoAnalyses",
    description="Video analysis results from video_analyze and video_batch_analyze",
    properties=_common_properties() + [
        PropertyDef(
            "video_id", ["text"], "YouTube video ID or file hash",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "source_url", ["text"], "Source URL or file path",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("instruction", ["text"], "Analysis instruction used"),
        PropertyDef("title", ["text"], "Video title"),
        PropertyDef("summary", ["text"], "Analysis summary"),
        PropertyDef("key_points", ["text[]"], "Key points extracted"),
        PropertyDef(
            "raw_result", ["text"], "Full JSON result",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "timestamps_json", ["text"], "Timestamps as JSON array",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("topics", ["text[]"], "Topics covered in the video"),
        PropertyDef(
            "sentiment", ["text"], "Overall sentiment",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "local_filepath", ["text"], "Local filesystem path to downloaded video file",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "screenshot_dir", ["text"], "Local filesystem path to screenshot directory",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
    references=[
        ReferenceDef("has_metadata", "VideoMetadata", "Link to video metadata"),
    ],
)

CONTENT_ANALYSES = CollectionDef(
    name="ContentAnalyses",
    description="Content analysis results from content_analyze",
    properties=_common_properties() + [
        PropertyDef(
            "source", ["text"], "Source URL, file path, or '(text)'",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("instruction", ["text"], "Analysis instruction used"),
        PropertyDef("title", ["text"], "Content title"),
        PropertyDef("summary", ["text"], "Analysis summary"),
        PropertyDef("key_points", ["text[]"], "Key points extracted"),
        PropertyDef("entities", ["text[]"], "Named entities found"),
        PropertyDef(
            "raw_result", ["text"], "Full JSON result",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("structure_notes", ["text"], "Content structure observations"),
        PropertyDef("quality_assessment", ["text"], "Content quality assessment"),
        PropertyDef(
            "local_filepath", ["text"], "Local filesystem path to the analyzed content file",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)

VIDEO_METADATA = CollectionDef(
    name="VideoMetadata",
    description="YouTube video metadata from video_metadata",
    properties=_common_properties() + [
        PropertyDef(
            "video_id", ["text"], "YouTube video ID",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("title", ["text"], "Video title"),
        PropertyDef("description", ["text"], "Video description"),
        PropertyDef("channel_title", ["text"], "Channel name"),
        PropertyDef("tags", ["text[]"], "Video tags"),
        PropertyDef(
            "view_count", ["int"], "View count",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "like_count", ["int"], "Like count",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "duration", ["text"], "Video duration",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "published_at", ["text"], "Publish date",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "channel_id", ["text"], "YouTube channel ID",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "comment_count", ["int"], "Comment count",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "duration_seconds", ["int"], "Duration in seconds",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef("category", ["text"], "Video category label"),
        PropertyDef(
            "definition", ["text"], "Video definition (hd/sd)",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("has_captions", ["boolean"], "Whether captions are available", skip_vectorization=True),
        PropertyDef(
            "default_language", ["text"], "Default language code",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)

SESSION_TRANSCRIPTS = CollectionDef(
    name="SessionTranscripts",
    description="Session turns from video_continue_session",
    properties=_common_properties() + [
        PropertyDef(
            "session_id", ["text"], "Session ID",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("video_title", ["text"], "Video title for this session"),
        PropertyDef(
            "turn_index", ["int"], "Turn number in session",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef("turn_prompt", ["text"], "User prompt for this turn"),
        PropertyDef("turn_response", ["text"], "Model response for this turn"),
        PropertyDef(
            "local_filepath", ["text"], "Local filesystem path to the session's video file",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)

WEB_SEARCH_RESULTS = CollectionDef(
    name="WebSearchResults",
    description="Web search results from web_search",
    properties=_common_properties() + [
        PropertyDef("query", ["text"], "Search query"),
        PropertyDef("response", ["text"], "Search response text"),
        PropertyDef(
            "sources_json", ["text"], "Grounding sources as JSON",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)

RESEARCH_PLANS = CollectionDef(
    name="ResearchPlans",
    description="Research orchestration plans from research_plan",
    properties=_common_properties() + [
        PropertyDef("topic", ["text"], "Research topic"),
        PropertyDef("scope", ["text"], "Research scope", skip_vectorization=True, index_searchable=False),
        PropertyDef("task_decomposition", ["text[]"], "Task breakdown"),
        PropertyDef(
            "phases_json", ["text"], "Phases as JSON",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "recommended_models_json", ["text"], "Recommended models as JSON",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)
