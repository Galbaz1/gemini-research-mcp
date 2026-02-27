"""Tests for Pydantic models."""

from gemini_research_mcp.models.video import (
    SessionInfo,
    SessionResponse,
    Timestamp,
    VideoResult,
)
from gemini_research_mcp.models.research import (
    EvidenceAssessment,
    Finding,
    FindingsContainer,
    Phase,
    ResearchPlan,
    ResearchReport,
    ResearchSynthesis,
)
from gemini_research_mcp.models.content import ContentResult


class TestVideoModels:
    def test_video_result_defaults(self):
        r = VideoResult()
        assert r.title == ""
        assert r.key_points == []
        assert r.timestamps == []
        assert r.topics == []

    def test_video_result_roundtrip(self):
        r = VideoResult(
            title="Test Video",
            summary="A summary",
            key_points=["point 1"],
            timestamps=[Timestamp(time="0:30", description="intro")],
            topics=["AI"],
            sentiment="positive",
        )
        d = r.model_dump()
        assert d["title"] == "Test Video"
        assert d["timestamps"][0]["time"] == "0:30"
        r2 = VideoResult.model_validate(d)
        assert r2.timestamps[0].description == "intro"

    def test_timestamp(self):
        t = Timestamp(time="1:23", description="Key moment")
        assert t.time == "1:23"
        assert t.description == "Key moment"

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

    def test_findings_container(self):
        fc = FindingsContainer(
            findings=[
                Finding(claim="A", evidence_tier="CONFIRMED"),
                Finding(claim="B", evidence_tier="INFERENCE"),
            ]
        )
        assert len(fc.findings) == 2
        assert fc.findings[0].evidence_tier == "CONFIRMED"

    def test_findings_container_roundtrip(self):
        fc = FindingsContainer(
            findings=[Finding(claim="X", supporting=["ev1", "ev2"])]
        )
        d = fc.model_dump()
        fc2 = FindingsContainer.model_validate(d)
        assert fc2.findings[0].supporting == ["ev1", "ev2"]

    def test_research_synthesis(self):
        s = ResearchSynthesis(
            executive_summary="Summary here",
            open_questions=["What about X?"],
            methodology_critique="Solid approach",
            recommendations=["Do Y"],
        )
        assert len(s.recommendations) == 1

    def test_research_synthesis_defaults(self):
        s = ResearchSynthesis()
        assert s.executive_summary == ""
        assert s.open_questions == []

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
    def test_content_result_defaults(self):
        r = ContentResult()
        assert r.title == ""
        assert r.summary == ""
        assert r.key_points == []
        assert r.entities == []
        assert r.structure_notes == ""
        assert r.quality_assessment == ""

    def test_content_result_roundtrip(self):
        r = ContentResult(
            title="Paper Title",
            summary="Overview",
            key_points=["A", "B"],
            entities=["Google", "Anthropic"],
            structure_notes="Well organized",
            quality_assessment="High quality",
        )
        d = r.model_dump()
        r2 = ContentResult.model_validate(d)
        assert r2.entities == ["Google", "Anthropic"]
