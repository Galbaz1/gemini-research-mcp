"""Tests for the context cache bridge — video_analyze → sessions → generate_content."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import video_research_mcp.config as cfg_mod
import video_research_mcp.context_cache as cc_mod
from video_research_mcp.sessions import SessionStore
from video_research_mcp.tools.video import (
    video_analyze,
    video_create_session,
    video_continue_session,
)

TEST_URL = "https://www.youtube.com/watch?v=GcNu6wrLTJc"
TEST_VIDEO_ID = "GcNu6wrLTJc"
TEST_CACHE_NAME = "cachedContents/test-bridge-123"


async def _passthrough_retry(fn):
    """Mock with_retry that just awaits the coroutine factory."""
    return await fn()


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Ensure cache registry is empty and _loaded reset between tests."""
    cc_mod._registry.clear()
    cc_mod._pending.clear()
    cc_mod._loaded = True
    yield
    cc_mod._registry.clear()
    cc_mod._pending.clear()
    cc_mod._loaded = True


@pytest.fixture(autouse=True)
def _isolate_registry_path(tmp_path):
    """Redirect registry persistence to temp dir — never touch real filesystem."""
    json_path = tmp_path / "context_cache_registry.json"
    with patch.object(cc_mod, "_registry_path", return_value=json_path):
        yield json_path


@pytest.fixture()
def _mock_session_store():
    """Provide an isolated in-memory session store."""
    store = SessionStore()
    with patch("video_research_mcp.tools.video.session_store", store):
        yield store


class TestVideoAnalyzePrewarm:
    async def test_video_analyze_prewarms_context_cache(self, mock_gemini_client):
        """GIVEN a YouTube URL WHEN video_analyze completes THEN fires cache pre-warm via start_prewarm."""
        from video_research_mcp.models.video import VideoResult

        mock_gemini_client["generate_structured"].return_value = VideoResult(
            title="Test", summary="Summary", key_points=["point"]
        )

        with patch.object(cc_mod, "start_prewarm", return_value=MagicMock()) as mock_prewarm:
            result = await video_analyze(url=TEST_URL, use_cache=False)

        assert "error" not in result
        mock_prewarm.assert_called_once()
        call_args = mock_prewarm.call_args
        assert call_args[0][0] == TEST_VIDEO_ID
        assert isinstance(call_args[0][1], list)
        assert call_args[0][1][0].file_data is not None


class TestCreateSessionCache:
    async def test_create_session_returns_cached_when_registry_hit(
        self, mock_gemini_client, _mock_session_store
    ):
        """GIVEN a pre-warmed registry WHEN video_create_session called THEN cache_status=cached."""
        cfg = cfg_mod.get_config()
        cc_mod._registry[(TEST_VIDEO_ID, cfg.default_model)] = TEST_CACHE_NAME

        mock_gemini_client["generate"].return_value = "Test Title"

        result = await video_create_session(url=TEST_URL)

        assert result["cache_status"] == "cached"
        session = _mock_session_store.get(result["session_id"])
        assert session.cache_name == TEST_CACHE_NAME
        assert session.model == cfg.default_model

    async def test_create_session_returns_uncached_when_registry_empty(
        self, mock_gemini_client, _mock_session_store
    ):
        """GIVEN empty registry WHEN video_create_session called THEN cache_status=uncached."""
        mock_gemini_client["generate"].return_value = "Test Title"

        result = await video_create_session(url=TEST_URL)

        assert result["cache_status"] == "uncached"
        session = _mock_session_store.get(result["session_id"])
        assert session.cache_name == ""


class TestContinueSessionCache:
    @pytest.fixture()
    def _cached_session(self, _mock_session_store):
        """Create a session with cache_name pre-set."""
        session = _mock_session_store.create(
            "https://www.youtube.com/watch?v=GcNu6wrLTJc",
            "general",
            video_title="Test",
            cache_name=TEST_CACHE_NAME,
            model="gemini-3.1-pro-preview",
        )
        return session

    @pytest.fixture()
    def _uncached_session(self, _mock_session_store):
        """Create a session without cache_name."""
        session = _mock_session_store.create(
            "https://www.youtube.com/watch?v=GcNu6wrLTJc",
            "general",
            video_title="Test",
        )
        return session

    async def test_continue_session_passes_cached_content(
        self, _cached_session, _mock_session_store
    ):
        """GIVEN a session with cache_name WHEN continue called THEN cached_content set."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch.object(cc_mod, "refresh_ttl", new_callable=AsyncMock, return_value=True),
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            result = await video_continue_session(
                session_id=_cached_session.session_id, prompt="Summarize"
            )

        assert "error" not in result
        call_kwargs = mock_client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.cached_content == TEST_CACHE_NAME
        # Verify model matches what the cache was created for
        model_used = call_kwargs.kwargs.get("model")
        assert model_used == "gemini-3.1-pro-preview"

    async def test_continue_session_uses_session_model_not_default(
        self, _mock_session_store
    ):
        """GIVEN a cached session with non-default model WHEN continue THEN uses session.model."""
        session = _mock_session_store.create(
            "https://www.youtube.com/watch?v=GcNu6wrLTJc",
            "general",
            video_title="Test",
            cache_name=TEST_CACHE_NAME,
            model="gemini-2.5-pro-custom",
        )

        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch.object(cc_mod, "refresh_ttl", new_callable=AsyncMock, return_value=True),
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            result = await video_continue_session(
                session_id=session.session_id, prompt="Summarize"
            )

        assert "error" not in result
        model_used = mock_client.aio.models.generate_content.call_args.kwargs["model"]
        assert model_used == "gemini-2.5-pro-custom"

    async def test_continue_session_falls_back_when_cache_expired(
        self, _cached_session, _mock_session_store
    ):
        """GIVEN a cached session WHEN refresh_ttl fails THEN falls back to inline video."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch.object(cc_mod, "refresh_ttl", new_callable=AsyncMock, return_value=False),
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            result = await video_continue_session(
                session_id=_cached_session.session_id, prompt="Summarize"
            )

        assert "error" not in result
        call_kwargs = mock_client.aio.models.generate_content.call_args
        # Should NOT have cached_content since cache expired
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert not hasattr(config, "cached_content") or config.cached_content is None
        # Should include video Part since we fell back
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        user_msg = contents[-1]
        assert len(user_msg.parts) == 2
        assert user_msg.parts[0].file_data is not None

    async def test_continue_session_omits_video_part_when_cached(
        self, _cached_session, _mock_session_store
    ):
        """GIVEN a cached session WHEN continue called THEN user content has text only."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch.object(cc_mod, "refresh_ttl", new_callable=AsyncMock, return_value=True),
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            await video_continue_session(
                session_id=_cached_session.session_id, prompt="Summarize"
            )

        call_kwargs = mock_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        user_msg = contents[-1]
        assert len(user_msg.parts) == 1
        assert user_msg.parts[0].text == "Summarize"
        assert user_msg.parts[0].file_data is None

    async def test_continue_session_refreshes_ttl(
        self, _cached_session, _mock_session_store
    ):
        """GIVEN a cached session WHEN continue called THEN refresh_ttl invoked."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch.object(cc_mod, "refresh_ttl", new_callable=AsyncMock, return_value=True) as mock_refresh,
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            await video_continue_session(
                session_id=_cached_session.session_id, prompt="Summarize"
            )

        mock_refresh.assert_called_once_with(TEST_CACHE_NAME)

    async def test_continue_session_includes_video_part_when_uncached(
        self, _uncached_session, _mock_session_store
    ):
        """GIVEN an uncached session WHEN continue called THEN user content has video+text."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Answer", thought=False)]))
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("video_research_mcp.tools.video.GeminiClient.get", return_value=mock_client),
            patch("video_research_mcp.tools.video.with_retry", side_effect=_passthrough_retry),
            patch("video_research_mcp.weaviate_store.store_session_turn", new_callable=AsyncMock),
        ):
            await video_continue_session(
                session_id=_uncached_session.session_id, prompt="Summarize"
            )

        call_kwargs = mock_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        user_msg = contents[-1]
        assert len(user_msg.parts) == 2
        assert user_msg.parts[0].file_data is not None
        assert user_msg.parts[1].text == "Summarize"

        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert not hasattr(config, "cached_content") or config.cached_content is None
