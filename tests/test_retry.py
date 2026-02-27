"""Tests for retry logic with exponential backoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import video_research_mcp.config as cfg_mod
from video_research_mcp.retry import _is_retryable, with_retry


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_mod._config = None
    yield
    cfg_mod._config = None


class TestIsRetryable:
    """Tests for _is_retryable pattern matching."""

    @pytest.mark.parametrize("msg", [
        "429 Too Many Requests",
        "Quota exceeded for this project",
        "RESOURCE_EXHAUSTED: rate limit",
        "Request timeout after 30s",
        "503 Service Temporarily Unavailable",
        "service unavailable, please retry",
    ])
    def test_is_retryable_patterns(self, msg: str):
        """Each known transient pattern should be recognized as retryable."""
        assert _is_retryable(Exception(msg)) is True

    @pytest.mark.parametrize("msg", [
        "Invalid input: missing required field",
        "Authentication failed",
        "400 Bad Request",
        "Permission denied",
        "Not found",
    ])
    def test_is_retryable_false_for_unknown(self, msg: str):
        """Non-transient errors should not be retryable."""
        assert _is_retryable(Exception(msg)) is False


class TestWithRetry:
    """Tests for with_retry exponential backoff behavior."""

    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_with_retry_success_first_attempt(self, mock_sleep):
        """No retry needed when the first attempt succeeds."""
        factory = AsyncMock(return_value="ok")

        result = await with_retry(factory)

        assert result == "ok"
        factory.assert_awaited_once()
        mock_sleep.assert_not_awaited()

    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_with_retry_succeeds_after_transient_error(self, mock_sleep):
        """Should retry on 429 and succeed on the second attempt."""
        factory = AsyncMock(side_effect=[Exception("429 rate limit"), "recovered"])

        result = await with_retry(factory)

        assert result == "recovered"
        assert factory.await_count == 2
        mock_sleep.assert_awaited_once()

    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_with_retry_exhausts_max_attempts(self, mock_sleep):
        """Should raise after all attempts fail with a retryable error."""
        factory = AsyncMock(side_effect=Exception("429 rate limit"))

        with pytest.raises(Exception, match="429 rate limit"):
            await with_retry(factory)

        assert factory.await_count == 3  # default max_attempts
        assert mock_sleep.await_count == 2  # sleeps between attempts, not after last

    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_with_retry_non_retryable_raises_immediately(self, mock_sleep):
        """Non-retryable errors should raise without any retry."""
        factory = AsyncMock(side_effect=ValueError("invalid input"))

        with pytest.raises(ValueError, match="invalid input"):
            await with_retry(factory)

        factory.assert_awaited_once()
        mock_sleep.assert_not_awaited()

    @patch("video_research_mcp.retry.random.random", return_value=0.0)
    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_backoff_delays_increase(self, mock_sleep, _mock_random):
        """Delays should follow exponential backoff: base*2^attempt."""
        factory = AsyncMock(
            side_effect=[
                Exception("429"),
                Exception("429"),
                "ok",
            ]
        )

        result = await with_retry(factory)

        assert result == "ok"
        delays = [call.args[0] for call in mock_sleep.await_args_list]
        assert delays == [1.0, 2.0]  # base_delay * 2^0, base_delay * 2^1

    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_respects_config_max_attempts(self, mock_sleep, monkeypatch):
        """Setting max_attempts=1 means no retry at all."""
        monkeypatch.setenv("GEMINI_RETRY_MAX_ATTEMPTS", "1")
        cfg_mod._config = None

        factory = AsyncMock(side_effect=Exception("429 rate limit"))

        with pytest.raises(Exception, match="429 rate limit"):
            await with_retry(factory)

        factory.assert_awaited_once()
        mock_sleep.assert_not_awaited()

    @patch("video_research_mcp.retry.random.random", return_value=0.0)
    @patch("video_research_mcp.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_respects_config_delays(self, mock_sleep, _mock_random, monkeypatch):
        """Custom base_delay and max_delay should be honored."""
        monkeypatch.setenv("GEMINI_RETRY_BASE_DELAY", "0.5")
        monkeypatch.setenv("GEMINI_RETRY_MAX_DELAY", "1.5")
        monkeypatch.setenv("GEMINI_RETRY_MAX_ATTEMPTS", "4")
        cfg_mod._config = None

        factory = AsyncMock(
            side_effect=[
                Exception("503"),
                Exception("503"),
                Exception("503"),
                "ok",
            ]
        )

        result = await with_retry(factory)

        assert result == "ok"
        delays = [call.args[0] for call in mock_sleep.await_args_list]
        # base=0.5: 0.5*1=0.5, 0.5*2=1.0, 0.5*4=2.0 capped at 1.5
        assert delays == [0.5, 1.0, 1.5]
