"""Tests for strict video contract Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from video_research_mcp.models.video_contract import (
    ConceptMap,
    ConceptMapEdge,
    ConceptMapNode,
    QualityReport,
    StrictTimestamp,
    StrictVideoResult,
    StrategyReport,
    StrategySection,
)


class TestStrictTimestamp:
    def test_valid_timestamp(self):
        ts = StrictTimestamp(time="01:23", description="Speaker introduces the main topic")
        assert ts.time == "01:23"

    def test_time_too_short(self):
        with pytest.raises(ValidationError, match="time"):
            StrictTimestamp(time="1", description="valid description text")

    def test_description_too_short(self):
        with pytest.raises(ValidationError, match="description"):
            StrictTimestamp(time="01:23", description="short")


class TestStrictVideoResult:
    def test_valid_result(self):
        result = StrictVideoResult(
            title="Test Video",
            summary="A" * 50,
            key_points=["point one detail", "point two detail", "point three detail"],
            timestamps=[
                StrictTimestamp(time="00:00", description="Introduction segment begins"),
                StrictTimestamp(time="01:00", description="Main topic discussion starts"),
                StrictTimestamp(time="05:00", description="Conclusion and final thoughts"),
            ],
            topics=["testing"],
            sentiment="positive",
        )
        assert result.title == "Test Video"

    def test_summary_too_short(self):
        with pytest.raises(ValidationError, match="summary"):
            StrictVideoResult(
                title="T",
                summary="Too short",
                key_points=["a", "b", "c"],
                timestamps=[
                    StrictTimestamp(time="00:00", description="Introduction segment begins"),
                    StrictTimestamp(time="01:00", description="Main topic segment"),
                    StrictTimestamp(time="02:00", description="Conclusion segment"),
                ],
                topics=["x"],
                sentiment="ok",
            )

    def test_too_few_timestamps(self):
        with pytest.raises(ValidationError, match="timestamps"):
            StrictVideoResult(
                title="T",
                summary="A" * 50,
                key_points=["a", "b", "c"],
                timestamps=[StrictTimestamp(time="00:00", description="Only one timestamp here")],
                topics=["x"],
                sentiment="ok",
            )


class TestStrategyReport:
    def test_valid_report(self):
        report = StrategyReport(
            title="Strategy",
            sections=[StrategySection(heading="Overview", content="A" * 20)],
            strategic_notes=["Key takeaway one"],
        )
        assert len(report.sections) == 1


class TestConceptMap:
    def test_valid_concept_map(self):
        cm = ConceptMap(
            nodes=[
                ConceptMapNode(id="a", label="Node A"),
                ConceptMapNode(id="b", label="Node B"),
            ],
            edges=[ConceptMapEdge(source="a", target="b", label="relates to")],
        )
        assert len(cm.nodes) == 2

    def test_too_few_nodes(self):
        with pytest.raises(ValidationError, match="nodes"):
            ConceptMap(
                nodes=[ConceptMapNode(id="a", label="Alone")],
                edges=[ConceptMapEdge(source="a", target="b")],
            )


class TestQualityReport:
    def test_coverage_bounds(self):
        with pytest.raises(ValidationError, match="coverage_ratio"):
            QualityReport(status="fail", coverage_ratio=1.5)
