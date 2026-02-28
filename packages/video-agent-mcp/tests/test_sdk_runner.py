"""Tests for sdk_runner — single and parallel agent query execution."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest

from video_agent_mcp.sdk_runner import run_agent_query, run_parallel_queries

from .conftest import MockAsyncIterator, make_mock_message


SAMPLE_TSX = """import React from "react";
import { AbsoluteFill } from "remotion";

export const HookScene: React.FC = () => {
  return <AbsoluteFill><div>Hook</div></AbsoluteFill>;
};"""


# ---------------------------------------------------------------------------
# run_agent_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_success():
    """GIVEN a normal agent response WHEN querying THEN returns success."""
    mock_msg = make_mock_message(SAMPLE_TSX)

    with patch("video_agent_mcp.sdk_runner.claude_agent_sdk") as mock_sdk:
        mock_sdk.ClaudeAgentOptions = MagicMock
        mock_sdk.query.return_value = MockAsyncIterator([mock_msg])

        result = await run_agent_query("Generate a scene")

    assert result.success is True
    assert "HookScene" in result.text
    assert result.duration_seconds > 0
    assert result.error is None


@pytest.mark.asyncio
async def test_query_timeout():
    """GIVEN a query that exceeds timeout WHEN querying THEN returns timeout error."""

    async def slow_generator(*args, **kwargs):
        yield make_mock_message("starting...")
        await asyncio.sleep(10)  # Will be cancelled by timeout
        yield make_mock_message("done")

    with patch("video_agent_mcp.sdk_runner.claude_agent_sdk") as mock_sdk:
        mock_sdk.ClaudeAgentOptions = MagicMock
        mock_sdk.query.return_value = slow_generator()

        result = await run_agent_query("Generate a scene", timeout=0)

    assert result.success is False
    assert "timed out" in result.error


@pytest.mark.asyncio
async def test_query_empty_response():
    """GIVEN an empty agent response WHEN querying THEN returns error."""
    mock_msg = make_mock_message("")

    with patch("video_agent_mcp.sdk_runner.claude_agent_sdk") as mock_sdk:
        mock_sdk.ClaudeAgentOptions = MagicMock
        mock_sdk.query.return_value = MockAsyncIterator([mock_msg])

        result = await run_agent_query("Generate a scene")

    assert result.success is False
    assert "Empty response" in result.error


@pytest.mark.asyncio
async def test_query_exception():
    """GIVEN an SDK exception WHEN querying THEN returns error gracefully."""
    with patch("video_agent_mcp.sdk_runner.claude_agent_sdk") as mock_sdk:
        mock_sdk.ClaudeAgentOptions = MagicMock
        mock_sdk.query.side_effect = RuntimeError("SDK connection failed")

        result = await run_agent_query("Generate a scene")

    assert result.success is False
    assert "SDK connection failed" in result.error


# ---------------------------------------------------------------------------
# run_parallel_queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_concurrency():
    """GIVEN 5 queries with concurrency=2 WHEN running THEN respects limit."""
    active = {"count": 0, "max": 0}

    async def mock_query(*args, **kwargs):
        yield make_mock_message("ok")

    original_run = run_agent_query

    async def counting_query(**kwargs):
        active["count"] += 1
        active["max"] = max(active["max"], active["count"])
        # Simulate some work
        await asyncio.sleep(0.01)
        result = await original_run(**kwargs)
        active["count"] -= 1
        return result

    queries = [{"prompt": f"Scene {i}"} for i in range(5)]

    with (
        patch("video_agent_mcp.sdk_runner.claude_agent_sdk") as mock_sdk,
        patch("video_agent_mcp.sdk_runner.run_agent_query", side_effect=counting_query),
    ):
        mock_sdk.ClaudeAgentOptions = MagicMock
        mock_sdk.query.return_value = MockAsyncIterator([make_mock_message("ok")])

        results = await run_parallel_queries(queries, concurrency=2)

    assert len(results) == 5
    assert active["max"] <= 2


@pytest.mark.asyncio
async def test_parallel_env_guard():
    """GIVEN CLAUDECODE is set WHEN running parallel THEN it's cleared during execution."""
    os.environ["CLAUDECODE"] = "/path/to/claude"
    captured_env: list[str | None] = []

    async def capture_env_query(**kwargs):
        captured_env.append(os.environ.get("CLAUDECODE"))
        return MagicMock(success=True, text="ok", error=None, duration_seconds=0.1)

    queries = [{"prompt": "test"}]

    with patch("video_agent_mcp.sdk_runner.run_agent_query", side_effect=capture_env_query):
        await run_parallel_queries(queries, concurrency=1)

    # CLAUDECODE should have been cleared during execution
    assert captured_env[0] is None
    # And restored after
    assert os.environ.get("CLAUDECODE") == "/path/to/claude"
    # Cleanup
    del os.environ["CLAUDECODE"]


@pytest.mark.asyncio
async def test_parallel_partial_failure():
    """GIVEN some queries fail WHEN running parallel THEN all results returned."""
    call_count = {"n": 0}

    async def alternating_query(**kwargs):
        call_count["n"] += 1
        if call_count["n"] % 2 == 0:
            return MagicMock(success=False, text="", error="Failed", duration_seconds=0.1)
        return MagicMock(success=True, text="ok", error=None, duration_seconds=0.1)

    queries = [{"prompt": f"Scene {i}"} for i in range(4)]

    with patch("video_agent_mcp.sdk_runner.run_agent_query", side_effect=alternating_query):
        results = await run_parallel_queries(queries, concurrency=4)

    assert len(results) == 4
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    assert succeeded == 2
    assert failed == 2
