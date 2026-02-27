"""Tests for Weaviate schema definitions."""

from __future__ import annotations

from video_research_mcp.weaviate_schema import (
    ALL_COLLECTIONS,
    CONTENT_ANALYSES,
    RESEARCH_FINDINGS,
    RESEARCH_PLANS,
    VIDEO_ANALYSES,
    VIDEO_METADATA,
)


class TestCollectionDefinitions:
    """Verify all 7 collections are defined correctly."""

    def test_all_collections_count(self):
        """ALL_COLLECTIONS contains exactly 7 collections."""
        assert len(ALL_COLLECTIONS) == 7

    def test_collection_names(self):
        """All expected collection names are present."""
        names = {c.name for c in ALL_COLLECTIONS}
        expected = {
            "ResearchFindings", "VideoAnalyses", "ContentAnalyses",
            "VideoMetadata", "SessionTranscripts", "WebSearchResults", "ResearchPlans",
        }
        assert names == expected

    def test_every_collection_has_created_at(self):
        """Every collection includes a created_at date property."""
        for col in ALL_COLLECTIONS:
            prop_names = [p.name for p in col.properties]
            assert "created_at" in prop_names, f"{col.name} missing created_at"

    def test_every_collection_has_source_tool(self):
        """Every collection includes a source_tool text property."""
        for col in ALL_COLLECTIONS:
            prop_names = [p.name for p in col.properties]
            assert "source_tool" in prop_names, f"{col.name} missing source_tool"


class TestNewProperties:
    """Verify the 18 new properties are defined in the correct collections."""

    def test_video_analyses_has_new_properties(self):
        """VideoAnalyses has timestamps_json, topics, sentiment."""
        names = {p.name for p in VIDEO_ANALYSES.properties}
        assert "timestamps_json" in names
        assert "topics" in names
        assert "sentiment" in names

    def test_research_findings_has_new_properties(self):
        """ResearchFindings has supporting, contradicting, methodology_critique, recommendations, report_uuid."""
        names = {p.name for p in RESEARCH_FINDINGS.properties}
        for prop in ("supporting", "contradicting", "methodology_critique", "recommendations", "report_uuid"):
            assert prop in names, f"Missing {prop}"

    def test_content_analyses_has_new_properties(self):
        """ContentAnalyses has structure_notes, quality_assessment."""
        names = {p.name for p in CONTENT_ANALYSES.properties}
        assert "structure_notes" in names
        assert "quality_assessment" in names

    def test_video_metadata_has_new_properties(self):
        """VideoMetadata has 7 new properties."""
        names = {p.name for p in VIDEO_METADATA.properties}
        for prop in ("channel_id", "comment_count", "duration_seconds", "category",
                      "definition", "has_captions", "default_language"):
            assert prop in names, f"Missing {prop}"

    def test_research_plans_has_recommended_models(self):
        """ResearchPlans has recommended_models_json."""
        names = {p.name for p in RESEARCH_PLANS.properties}
        assert "recommended_models_json" in names

    def test_new_vectorization_flags(self):
        """New semantic fields are vectorized, metadata fields are not."""
        # Vectorized
        for name in ("supporting", "contradicting", "methodology_critique", "recommendations"):
            prop = next(p for p in RESEARCH_FINDINGS.properties if p.name == name)
            assert not prop.skip_vectorization, f"{name} should be vectorized"
        # Not vectorized
        prop = next(p for p in RESEARCH_FINDINGS.properties if p.name == "report_uuid")
        assert prop.skip_vectorization
        prop = next(p for p in VIDEO_ANALYSES.properties if p.name == "timestamps_json")
        assert prop.skip_vectorization
        prop = next(p for p in VIDEO_ANALYSES.properties if p.name == "sentiment")
        assert prop.skip_vectorization


class TestReferences:
    """Verify cross-reference definitions."""

    def test_video_analyses_has_metadata_reference(self):
        """VideoAnalyses has a has_metadata reference to VideoMetadata."""
        assert len(VIDEO_ANALYSES.references) == 1
        ref = VIDEO_ANALYSES.references[0]
        assert ref.name == "has_metadata"
        assert ref.target_collection == "VideoMetadata"

    def test_research_findings_has_report_reference(self):
        """ResearchFindings has a belongs_to_report self-reference."""
        assert len(RESEARCH_FINDINGS.references) == 1
        ref = RESEARCH_FINDINGS.references[0]
        assert ref.name == "belongs_to_report"
        assert ref.target_collection == "ResearchFindings"

    def test_collections_without_references(self):
        """Most collections have no references."""
        for col in ALL_COLLECTIONS:
            if col.name not in ("VideoAnalyses", "ResearchFindings"):
                assert len(col.references) == 0, f"{col.name} should have no references"


class TestToDict:
    """Verify to_dict() produces valid Weaviate-compatible structures."""

    def test_to_dict_has_class_key(self):
        """to_dict() uses 'class' key (not 'name') for Weaviate compatibility."""
        for col in ALL_COLLECTIONS:
            d = col.to_dict()
            assert "class" in d
            assert d["class"] == col.name

    def test_to_dict_has_properties(self):
        """to_dict() includes properties list."""
        for col in ALL_COLLECTIONS:
            d = col.to_dict()
            assert "properties" in d
            assert isinstance(d["properties"], list)
            assert len(d["properties"]) > 0

    def test_property_dict_structure(self):
        """Each property dict has name and dataType keys."""
        for col in ALL_COLLECTIONS:
            d = col.to_dict()
            for prop in d["properties"]:
                assert "name" in prop
                assert "dataType" in prop


class TestVectorizeFlags:
    """Verify skip_vectorization flags are correct."""

    def test_created_at_skips_vectorization(self):
        """created_at should skip vectorization in all collections."""
        for col in ALL_COLLECTIONS:
            prop = next(p for p in col.properties if p.name == "created_at")
            assert prop.skip_vectorization is True, f"{col.name}.created_at should skip"

    def test_source_tool_skips_vectorization(self):
        """source_tool should skip vectorization in all collections."""
        for col in ALL_COLLECTIONS:
            prop = next(p for p in col.properties if p.name == "source_tool")
            assert prop.skip_vectorization is True, f"{col.name}.source_tool should skip"

    def test_research_findings_vectorized_fields(self):
        """ResearchFindings vectorizes claim, reasoning, executive_summary."""
        vectorized = [
            p.name for p in RESEARCH_FINDINGS.properties if not p.skip_vectorization
        ]
        assert "claim" in vectorized
        assert "reasoning" in vectorized
        assert "executive_summary" in vectorized

    def test_video_analyses_vectorized_fields(self):
        """VideoAnalyses vectorizes title, summary, key_points, topics."""
        vectorized = [
            p.name for p in VIDEO_ANALYSES.properties if not p.skip_vectorization
        ]
        assert "title" in vectorized
        assert "summary" in vectorized
        assert "key_points" in vectorized
        assert "topics" in vectorized

    def test_skip_vectorization_in_dict(self):
        """Properties with skip=True include moduleConfig in to_dict()."""
        prop = next(p for p in RESEARCH_FINDINGS.properties if p.name == "created_at")
        d = prop.to_dict()
        assert "moduleConfig" in d
        assert d["moduleConfig"]["text2vec-weaviate"]["skip"] is True

    def test_no_skip_vectorization_in_dict(self):
        """Properties with skip=False do NOT include moduleConfig."""
        prop = next(p for p in RESEARCH_FINDINGS.properties if p.name == "claim")
        d = prop.to_dict()
        assert "moduleConfig" not in d
