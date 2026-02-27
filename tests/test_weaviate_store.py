"""Tests for Weaviate write-through store functions."""

from __future__ import annotations



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
            {"title": "Test Video", "summary": "A test", "key_points": ["point1"]},
            "vid123", "summarize", "https://youtube.com/watch?v=vid123",
        )
        assert result == "test-uuid-1234"
        mock_weaviate_client["collection"].data.insert.assert_called_once()

    async def test_store_content_returns_uuid(self, mock_weaviate_client, clean_config, monkeypatch):
        """store_content_analysis returns UUID string when successful."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_content_analysis
        result = await store_content_analysis(
            {"title": "Test", "summary": "A test"}, "http://example.com", "summarize",
        )
        assert result == "test-uuid-1234"

    async def test_store_research_creates_n_plus_1_objects(
        self, mock_weaviate_client, clean_config, monkeypatch
    ):
        """store_research_finding creates report + N finding objects."""
        monkeypatch.setenv("WEAVIATE_URL", "https://test.weaviate.network")
        from video_research_mcp.weaviate_store import store_research_finding
        report = {
            "topic": "AI",
            "scope": "moderate",
            "executive_summary": "Summary",
            "findings": [
                {"claim": "Claim 1", "evidence_tier": "CONFIRMED", "reasoning": "R1"},
                {"claim": "Claim 2", "evidence_tier": "INFERENCE", "reasoning": "R2"},
            ],
            "open_questions": [],
        }
        result = await store_research_finding(report)
        assert result is not None
        assert len(result) == 3  # 1 report + 2 findings
        assert mock_weaviate_client["collection"].data.insert.call_count == 3

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
