"""Tests for Pydantic models."""

from video_research_mcp.models.video import (
    SessionInfo,
    SessionResponse,
    Timestamp,
    VideoResult,
)
from video_research_mcp.models.research import (
    EvidenceAssessment,
    Finding,
    FindingsContainer,
    Phase,
    ResearchPlan,
    ResearchReport,
    ResearchSynthesis,
)
from video_research_mcp.models.content import ContentResult
from video_research_mcp.models.video_batch import BatchVideoItem, BatchVideoResult


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
        assert s.source_type == ""

    def test_session_info_source_type(self):
        s = SessionInfo(session_id="abc", source_type="youtube")
        assert s.source_type == "youtube"

    def test_session_response(self):
        r = SessionResponse(response="Analysis here", turn_count=3)
        assert r.turn_count == 3


class TestBatchVideoModels:
    def test_batch_item_defaults(self):
        item = BatchVideoItem(file_name="a.mp4", file_path="/tmp/a.mp4")
        assert item.result == {}
        assert item.error == ""

    def test_batch_item_with_error(self):
        item = BatchVideoItem(file_name="b.mp4", file_path="/tmp/b.mp4", error="fail")
        assert item.error == "fail"

    def test_batch_result_defaults(self):
        r = BatchVideoResult(directory="/tmp", total_files=0, successful=0, failed=0)
        assert r.items == []

    def test_batch_result_roundtrip(self):
        r = BatchVideoResult(
            directory="/videos",
            total_files=2,
            successful=1,
            failed=1,
            items=[
                BatchVideoItem(file_name="a.mp4", file_path="/videos/a.mp4", result={"title": "A"}),
                BatchVideoItem(file_name="b.mp4", file_path="/videos/b.mp4", error="timeout"),
            ],
        )
        d = r.model_dump()
        assert d["total_files"] == 2
        r2 = BatchVideoResult.model_validate(d)
        assert r2.items[1].error == "timeout"


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
