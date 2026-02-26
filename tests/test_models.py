"""Tests for Pydantic models."""

from gemini_research_mcp.models.video import (
    ComparisonResult,
    SessionInfo,
    SessionResponse,
    VideoAnalysis,
)
from gemini_research_mcp.models.research import (
    EvidenceAssessment,
    Finding,
    Phase,
    ResearchPlan,
    ResearchReport,
)
from gemini_research_mcp.models.content import DocumentAnalysis, Summary


class TestVideoModels:
    def test_video_analysis_defaults(self):
        a = VideoAnalysis(url="https://youtube.com/watch?v=abc")
        assert a.mode == "general"
        assert a.commands == []
        assert a.cached is False

    def test_video_analysis_roundtrip(self):
        a = VideoAnalysis(
            url="https://youtube.com/watch?v=abc",
            mode="tutorial",
            title="Test Video",
            commands=["npm install"],
        )
        d = a.model_dump()
        assert d["title"] == "Test Video"
        assert d["commands"] == ["npm install"]

    def test_comparison_result(self):
        c = ComparisonResult(
            common_themes=["AI", "testing"],
            recommendation="Watch video A first",
        )
        assert len(c.common_themes) == 2

    def test_session_info(self):
        s = SessionInfo(session_id="abc123", video_title="Test")
        assert s.status == "created"

    def test_session_response(self):
        r = SessionResponse(response="Analysis here", turn_count=3)
        assert r.turn_count == 3


class TestResearchModels:
    def test_finding_defaults(self):
        f = Finding(claim="X causes Y")
        assert f.evidence_tier == "UNKNOWN"
        assert f.supporting == []

    def test_research_report(self):
        r = ResearchReport(
            topic="AI Safety",
            findings=[Finding(claim="Risk exists", evidence_tier="CONFIRMED")],
        )
        assert len(r.findings) == 1
        assert r.scope == "moderate"

    def test_research_plan(self):
        p = ResearchPlan(
            topic="Quantum ML",
            scope="focused",
            phases=[Phase(name="Scan", description="Scan papers", recommended_model="haiku")],
        )
        assert p.phases[0].recommended_model == "haiku"

    def test_evidence_assessment(self):
        e = EvidenceAssessment(claim="Safe", tier="INFERENCE", confidence=0.7)
        assert e.confidence == 0.7


class TestContentModels:
    def test_document_analysis(self):
        d = DocumentAnalysis(summary="Overview", key_points=["A", "B"])
        assert len(d.key_points) == 2

    def test_summary(self):
        s = Summary(text="Short version", word_count=2, key_takeaways=["Main point"])
        assert s.word_count == 2
