"""Core Agent SDK wrapper — single and parallel query execution.

Provides ``run_agent_query()`` for individual queries and
``run_parallel_queries()`` for bounded concurrent execution via
``asyncio.gather()`` + ``Semaphore``.

Critical: The CLAUDECODE env variable must be cleared before spawning
nested Claude instances to prevent recursive agent loops. This guard
is applied once at the orchestration level in ``run_parallel_queries()``,
not per-query.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

import claude_agent_sdk

from .config import get_config
from .types import AgentResult

logger = logging.getLogger(__name__)


async def run_agent_query(
    prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_turns: int | None = None,
    timeout: int | None = None,
) -> AgentResult:
    """Execute a single Agent SDK query.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt override.
        model: Claude model ID. Defaults to config.agent_model.
        max_turns: Max conversation turns. Defaults to config.agent_max_turns.
        timeout: Query timeout in seconds. Defaults to config.agent_timeout.

    Returns:
        AgentResult with the response text, success status, and timing.
    """
    cfg = get_config()
    model = model or cfg.agent_model
    max_turns = max_turns if max_turns is not None else cfg.agent_max_turns
    timeout = timeout if timeout is not None else cfg.agent_timeout

    options = claude_agent_sdk.ClaudeAgentOptions(
        max_turns=max_turns,
        model=model,
    )
    if system_prompt:
        options.system_prompt = system_prompt

    start = time.monotonic()
    text_parts: list[str] = []

    try:
        async with asyncio.timeout(timeout):
            async for message in claude_agent_sdk.query(
                prompt=prompt,
                options=options,
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)

        elapsed = time.monotonic() - start
        full_text = "\n".join(text_parts)

        if not full_text.strip():
            return AgentResult(
                text="",
                success=False,
                duration_seconds=elapsed,
                error="Empty response from agent",
            )

        return AgentResult(
            text=full_text,
            success=True,
            duration_seconds=elapsed,
        )

    except TimeoutError:
        elapsed = time.monotonic() - start
        return AgentResult(
            text="",
            success=False,
            duration_seconds=elapsed,
            error=f"Agent query timed out after {timeout}s",
        )
    except Exception as exc:
        elapsed = time.monotonic() - start
        return AgentResult(
            text="",
            success=False,
            duration_seconds=elapsed,
            error=str(exc),
        )


async def run_parallel_queries(
    queries: list[dict],
    *,
    concurrency: int | None = None,
) -> list[AgentResult]:
    """Run multiple agent queries in parallel with bounded concurrency.

    Clears the CLAUDECODE env var once before spawning to prevent nested
    agent recursion, then restores it in a finally block.

    Args:
        queries: List of dicts with keys matching ``run_agent_query()`` params
            (``prompt`` required; ``system_prompt``, ``model``, ``max_turns``,
            ``timeout`` optional).
        concurrency: Max parallel queries. Defaults to config.agent_concurrency.

    Returns:
        List of AgentResult in the same order as input queries.
    """
    cfg = get_config()
    concurrency = concurrency or cfg.agent_concurrency
    semaphore = asyncio.Semaphore(concurrency)

    # Guard: remove CLAUDECODE to prevent nested agent loops
    saved_claudecode = os.environ.pop("CLAUDECODE", None)

    async def _run_with_semaphore(query_kwargs: dict) -> AgentResult:
        async with semaphore:
            return await run_agent_query(**query_kwargs)

    try:
        logger.info(
            "Starting %d parallel queries (concurrency=%d)",
            len(queries),
            concurrency,
        )
        start = time.monotonic()
        results = await asyncio.gather(
            *[_run_with_semaphore(q) for q in queries],
            return_exceptions=False,
        )
        elapsed = time.monotonic() - start
        succeeded = sum(1 for r in results if r.success)
        logger.info(
            "Parallel queries done: %d/%d succeeded in %.1fs",
            succeeded,
            len(queries),
            elapsed,
        )
        return list(results)
    finally:
        # Restore CLAUDECODE if it was set
        if saved_claudecode is not None:
            os.environ["CLAUDECODE"] = saved_claudecode
