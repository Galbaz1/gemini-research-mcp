"""Tests for Weaviate write-through store functions."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestStoreGuards:
    """Test that all store functions respect the enabled guard."""

    async def test_store_video_noop_when_disabled(self, mock_weaviate_disabled):
        """store_video_analysis returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_video_analysis
        result = await store_video_analysis({"title": "test"}, "vid123", "summarize")
        assert result is None

    async def test_store_content_noop_when_disabled(self, mock_weaviate_disabled):
        """store_content_analysis returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_content_analysis
        result = await store_content_analysis({"title": "test"}, "http://example.com", "summarize")
        assert result is None

    async def test_store_research_noop_when_disabled(self, mock_weaviate_disabled):
        """store_research_finding returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_research_finding
        result = await store_research_finding({"topic": "AI", "findings": []})
        assert result is None

    async def test_store_plan_noop_when_disabled(self, mock_weaviate_disabled):
        """store_research_plan returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_research_plan
        result = await store_research_plan({"topic": "AI"})
        assert result is None

    async def test_store_evidence_noop_when_disabled(self, mock_weaviate_disabled):
        """store_evidence_assessment returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_evidence_assessment
        result = await store_evidence_assessment({"claim": "test"})
        assert result is None

    async def test_store_metadata_noop_when_disabled(self, mock_weaviate_disabled):
        """store_video_metadata returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_video_metadata
        result = await store_video_metadata({"video_id": "abc"})
        assert result is None

    async def test_store_session_noop_when_disabled(self, mock_weaviate_disabled):
        """store_session_turn returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_session_turn
        result = await store_session_turn("sess1", "Video", 1, "prompt", "response")
        assert result is None

    async def test_store_search_noop_when_disabled(self, mock_weaviate_disabled):
        """store_web_search returns None when Weaviate is disabled."""
        from video_research_mcp.weaviate_store import store_web_search
        result = await store_web_search("query", "response", [])
        assert result is None


class TestStoreWhenEnabled:
    """Test that store functions write to Weaviate when enabled."""

    async def test_store_video_returns_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_video_analysis returns UUID string when successful."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_video_analysis
        result = await store_video_analysis(
            {"title": "Test Video", "summary": "A test", "key_points": ["point1"],
             "timestamps": [{"t": "00:01"}], "topics": ["AI"], "sentiment": "positive"},
            "vid123", "summarize", "https://youtube.com/watch?v=vid123",
        )
        assert result == "test-uuid-1234"
        mock_weaviate_client["collection"].data.insert.assert_called_once()

    async def test_store_video_includes_new_fields(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_video_analysis passes timestamps_json, topics, sentiment."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_video_analysis
        await store_video_analysis(
            {"title": "V", "timestamps": [{"t": "1:00"}], "topics": ["ML"], "sentiment": "neutral"},
            "vid1", "analyze",
        )
        call_props = mock_weaviate_client["collection"].data.insert.call_args[1]["properties"]
        assert "timestamps_json" in call_props
        assert call_props["topics"] == ["ML"]
        assert call_props["sentiment"] == "neutral"

    async def test_store_video_adds_cross_ref(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_video_analysis calls reference_add for has_metadata."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_video_analysis
        await store_video_analysis({"title": "V"}, "vid1", "analyze")
        mock_weaviate_client["collection"].data.reference_add.assert_called_once()

    async def test_store_video_cross_ref_failure_nonfatal(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_video_analysis succeeds even if cross-ref fails."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.reference_add.side_effect = Exception("ref failed")
        from video_research_mcp.weaviate_store import store_video_analysis
        result = await store_video_analysis({"title": "V"}, "vid1", "analyze")
        assert result is not None

    async def test_store_content_returns_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_content_analysis returns UUID string when successful."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_content_analysis
        result = await store_content_analysis(
            {"title": "Test", "summary": "A test"}, "http://example.com", "summarize",
        )
        assert result == "test-uuid-1234"

    async def test_store_content_includes_new_fields(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_content_analysis passes structure_notes and quality_assessment."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_content_analysis
        await store_content_analysis(
            {"title": "C", "structure_notes": "Well-organized", "quality_assessment": "High quality"},
            "http://example.com", "analyze",
        )
        call_props = mock_weaviate_client["collection"].data.insert.call_args[1]["properties"]
        assert call_props["structure_notes"] == "Well-organized"
        assert call_props["quality_assessment"] == "High quality"

    async def test_store_research_uses_insert_many(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_research_finding uses insert_many for batch import."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")

        # Mock insert_many return
        mock_obj1 = MagicMock()
        mock_obj1.uuid = "report-uuid"
        mock_obj2 = MagicMock()
        mock_obj2.uuid = "finding-uuid-1"
        mock_result = MagicMock()
        mock_result.all_objects = [mock_obj1, mock_obj2]
        mock_weaviate_client["collection"].data.insert_many.return_value = mock_result

        from video_research_mcp.weaviate_store import store_research_finding
        report = {
            "topic": "AI",
            "scope": "moderate",
            "executive_summary": "Summary",
            "findings": [
                {"claim": "Claim 1", "evidence_tier": "CONFIRMED", "reasoning": "R1",
                 "supporting": ["src1"], "contradicting": []},
            ],
            "open_questions": [],
            "methodology_critique": "Solid",
            "recommendations": ["Rec1"],
        }
        result = await store_research_finding(report)
        assert result is not None
        assert len(result) == 2
        # Verify insert_many was called instead of individual inserts
        mock_weaviate_client["collection"].data.insert_many.assert_called_once()
        mock_weaviate_client["collection"].data.insert.assert_not_called()

    async def test_store_research_adds_cross_refs(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_research_finding adds belongs_to_report references."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")

        mock_obj1 = MagicMock()
        mock_obj1.uuid = "report-uuid"
        mock_obj2 = MagicMock()
        mock_obj2.uuid = "finding-uuid-1"
        mock_obj3 = MagicMock()
        mock_obj3.uuid = "finding-uuid-2"
        mock_result = MagicMock()
        mock_result.all_objects = [mock_obj1, mock_obj2, mock_obj3]
        mock_weaviate_client["collection"].data.insert_many.return_value = mock_result

        from video_research_mcp.weaviate_store import store_research_finding
        report = {
            "topic": "AI", "findings": [
                {"claim": "C1", "evidence_tier": "CONFIRMED"},
                {"claim": "C2", "evidence_tier": "INFERENCE"},
            ],
        }
        await store_research_finding(report)
        # 2 findings → 2 reference_add calls + 2 update calls
        assert mock_weaviate_client["collection"].data.reference_add.call_count == 2
        assert mock_weaviate_client["collection"].data.update.call_count == 2

    async def test_store_evidence_includes_new_fields(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_evidence_assessment passes supporting and contradicting."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_evidence_assessment
        await store_evidence_assessment({
            "claim": "Test claim",
            "tier": "CONFIRMED",
            "reasoning": "Good evidence",
            "confidence": 0.9,
            "supporting": ["source1", "source2"],
            "contradicting": ["source3"],
        })
        call_props = mock_weaviate_client["collection"].data.insert.call_args[1]["properties"]
        assert call_props["supporting"] == ["source1", "source2"]
        assert call_props["contradicting"] == ["source3"]

    async def test_store_plan_includes_recommended_models(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_research_plan passes recommended_models_json."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_research_plan
        await store_research_plan({
            "topic": "AI",
            "recommended_models": ["gemini-pro", "claude-opus"],
        })
        call_props = mock_weaviate_client["collection"].data.insert.call_args[1]["properties"]
        assert "recommended_models_json" in call_props
        assert "gemini-pro" in call_props["recommended_models_json"]

    async def test_store_metadata_includes_new_fields(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_video_metadata passes all 7 new fields."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_video_metadata
        await store_video_metadata({
            "video_id": "abc",
            "title": "Test",
            "channel_id": "UC123",
            "comment_count": 42,
            "duration_seconds": 300,
            "category": "Education",
            "definition": "hd",
            "has_captions": True,
            "default_language": "en",
        })
        call_props = mock_weaviate_client["collection"].data.replace.call_args[1]["properties"]
        assert call_props["channel_id"] == "UC123"
        assert call_props["comment_count"] == 42
        assert call_props["duration_seconds"] == 300
        assert call_props["category"] == "Education"
        assert call_props["definition"] == "hd"
        assert call_props["has_captions"] is True
        assert call_props["default_language"] == "en"

    async def test_store_metadata_dedup_replaces_existing(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_video_metadata uses replace with deterministic UUID for dedup."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        import weaviate.util
        expected_uuid = str(weaviate.util.generate_uuid5("abc"))

        from video_research_mcp.weaviate_store import store_video_metadata
        result = await store_video_metadata({"video_id": "abc", "title": "Test"})
        assert result == expected_uuid
        mock_weaviate_client["collection"].data.replace.assert_called_once()

    async def test_store_metadata_inserts_on_replace_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_video_metadata falls back to insert when replace fails (new object)."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.replace.side_effect = Exception("Not found")

        from video_research_mcp.weaviate_store import store_video_metadata
        result = await store_video_metadata({"video_id": "new_id", "title": "New"})
        assert result is not None
        mock_weaviate_client["collection"].data.insert.assert_called_once()


class TestStoreErrorHandling:
    """Test that store functions handle errors gracefully."""

    async def test_store_video_returns_none_on_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_video_analysis returns None (not raises) on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("Connection lost")

        from video_research_mcp.weaviate_store import store_video_analysis
        result = await store_video_analysis({"title": "test"}, "vid123", "summarize")
        assert result is None

    async def test_store_session_returns_none_on_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_session_turn returns None (not raises) on failure."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert.side_effect = RuntimeError("Timeout")

        from video_research_mcp.weaviate_store import store_session_turn
        result = await store_session_turn("sess1", "Video", 1, "prompt", "response")
        assert result is None

    async def test_store_research_returns_none_on_batch_failure(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_research_finding returns None when insert_many fails."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        mock_weaviate_client["collection"].data.insert_many.side_effect = RuntimeError("Batch failed")

        from video_research_mcp.weaviate_store import store_research_finding
        result = await store_research_finding({"topic": "AI", "findings": [{"claim": "C1"}]})
        assert result is None
