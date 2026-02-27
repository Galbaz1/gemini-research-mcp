"""Exponential backoff retry for transient Gemini API errors."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .config import get_config

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRYABLE_PATTERNS: tuple[str, ...] = (
    "429",
    "quota",
    "resource_exhausted",
    "timeout",
    "503",
    "service unavailable",
)


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception message matches known transient patterns."""
    msg = str(exc).lower()
    return any(p in msg for p in _RETRYABLE_PATTERNS)


async def with_retry(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Execute an async callable with exponential backoff on transient errors.

    Args:
        coro_factory: Zero-arg callable that returns a fresh awaitable each attempt.

    Returns:
        The result of the first successful call.

    Raises:
        The last exception if all attempts are exhausted or non-retryable.
    """
    cfg = get_config()
    max_attempts = cfg.retry_max_attempts
    base_delay = cfg.retry_base_delay
    max_delay = cfg.retry_max_delay

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == max_attempts - 1:
                raise
            delay = min(base_delay * (2 ** attempt) + random.random(), max_delay)
            logger.warning(
                "Retry %d/%d after %.1fs: %s", attempt + 1, max_attempts, delay, exc,
            )
            await asyncio.sleep(delay)
    raise last_exc  # unreachable but satisfies type checker
