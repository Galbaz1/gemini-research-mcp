"""Tests for knowledge filter builder."""

from __future__ import annotations

from video_research_mcp.tools.knowledge_filters import build_collection_filter

# Simulate allowed properties for different collections
_RESEARCH_PROPS = {"created_at", "source_tool", "topic", "evidence_tier", "claim", "report_uuid"}
_VIDEO_ANALYSIS_PROPS = {"created_at", "source_tool", "video_id", "title", "summary"}
_VIDEO_METADATA_PROPS = {"created_at", "source_tool", "video_id", "category", "channel_id"}


class TestBuildCollectionFilter:
    """Tests for build_collection_filter."""

    def test_returns_none_when_no_filters(self):
        """No filter params → None."""
        result = build_collection_filter("ResearchFindings", _RESEARCH_PROPS)
        assert result is None

    def test_evidence_tier_filter(self):
        """evidence_tier produces a filter for ResearchFindings."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, evidence_tier="CONFIRMED",
        )
        assert result is not None

    def test_evidence_tier_skipped_for_video_analyses(self):
        """evidence_tier is skipped for collections without that property."""
        result = build_collection_filter(
            "VideoAnalyses", _VIDEO_ANALYSIS_PROPS, evidence_tier="CONFIRMED",
        )
        assert result is None

    def test_source_tool_filter(self):
        """source_tool produces a filter (all collections have this)."""
        result = build_collection_filter(
            "VideoAnalyses", _VIDEO_ANALYSIS_PROPS, source_tool="video_analyze",
        )
        assert result is not None

    def test_date_from_filter(self):
        """date_from produces a >= filter."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, date_from="2025-01-01",
        )
        assert result is not None

    def test_date_to_filter(self):
        """date_to produces a <= filter."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, date_to="2025-12-31",
        )
        assert result is not None

    def test_category_filter(self):
        """category produces a filter for VideoMetadata."""
        result = build_collection_filter(
            "VideoMetadata", _VIDEO_METADATA_PROPS, category="Education",
        )
        assert result is not None

    def test_category_skipped_for_research(self):
        """category is skipped for collections without it."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, category="Education",
        )
        assert result is None

    def test_video_id_filter(self):
        """video_id produces a filter for collections with that property."""
        result = build_collection_filter(
            "VideoAnalyses", _VIDEO_ANALYSIS_PROPS, video_id="abc123",
        )
        assert result is not None

    def test_combined_filters(self):
        """Multiple applicable filters produce a combined filter."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS,
            evidence_tier="CONFIRMED", source_tool="research_deep",
            date_from="2025-01-01",
        )
        assert result is not None

    def test_invalid_date_ignored(self):
        """Invalid date strings are silently ignored."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, date_from="not-a-date",
        )
        assert result is None

    def test_empty_string_filters_ignored(self):
        """Empty string filter values are treated as None."""
        result = build_collection_filter(
            "ResearchFindings", _RESEARCH_PROPS, evidence_tier="", source_tool="",
        )
        assert result is None
