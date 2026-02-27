"""Tests for Weaviate schema definitions."""

from __future__ import annotations

from video_research_mcp.weaviate_schema import (
    ALL_COLLECTIONS,
    RESEARCH_FINDINGS,
    VIDEO_ANALYSES,
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
        """VideoAnalyses vectorizes title, summary, key_points."""
        vectorized = [
            p.name for p in VIDEO_ANALYSES.properties if not p.skip_vectorization
        ]
        assert "title" in vectorized
        assert "summary" in vectorized
        assert "key_points" in vectorized

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
