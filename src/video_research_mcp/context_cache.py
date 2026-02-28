"""Process-scoped registry for Gemini context caches.

Maps (content_id, model) → cache_name. All operations are best-effort;
failures return None/False and never raise.
"""

from __future__ import annotations

import logging

from google.genai import types

from .client import GeminiClient
from .config import get_config

logger = logging.getLogger(__name__)

_registry: dict[tuple[str, str], str] = {}


async def get_or_create(
    content_id: str,
    video_parts: list[types.Part],
    model: str,
) -> str | None:
    """Return an existing cache name or create one for the video content.

    Args:
        content_id: Stable identifier (YouTube video_id or file hash).
        video_parts: The video Part(s) to cache (file_data parts only).
        model: Model ID the cache will be used with.

    Returns:
        Cache resource name (e.g. "cachedContents/abc123") or None on failure.
    """
    key = (content_id, model)

    existing = _registry.get(key)
    if existing:
        try:
            client = GeminiClient.get()
            cached = await client.aio.caches.get(name=existing)
            if cached and cached.name:
                logger.debug("Context cache hit for %s → %s", content_id, existing)
                return existing
        except Exception:
            logger.debug("Stale cache entry for %s, recreating", content_id)
            _registry.pop(key, None)

    try:
        client = GeminiClient.get()
        cfg = get_config()
        ttl = f"{cfg.context_cache_ttl_seconds}s"

        contents = [types.Content(role="user", parts=video_parts)]
        cached = await client.aio.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                contents=contents,
                ttl=ttl,
                displayName=f"video-{content_id}",
            ),
        )
        if cached and cached.name:
            _registry[key] = cached.name
            logger.info(
                "Created context cache %s for %s (model=%s, ttl=%s)",
                cached.name, content_id, model, ttl,
            )
            return cached.name
    except Exception:
        logger.warning("Failed to create context cache for %s", content_id, exc_info=True)

    return None


async def refresh_ttl(cache_name: str) -> bool:
    """Extend the TTL of an active cache. Returns True on success."""
    try:
        client = GeminiClient.get()
        cfg = get_config()
        ttl = f"{cfg.context_cache_ttl_seconds}s"
        await client.aio.caches.update(
            name=cache_name,
            config=types.UpdateCachedContentConfig(ttl=ttl),
        )
        logger.debug("Refreshed TTL for cache %s", cache_name)
        return True
    except Exception:
        logger.debug("Failed to refresh TTL for cache %s", cache_name, exc_info=True)
        return False


def lookup(content_id: str, model: str) -> str | None:
    """Synchronous registry check — no API call."""
    return _registry.get((content_id, model))


async def clear() -> int:
    """Delete all tracked caches and clear the registry. Returns count cleared."""
    if not _registry:
        logger.info("Cleared 0 context cache(s)")
        return 0

    count = 0
    try:
        client = GeminiClient.get()
    except Exception:
        logger.warning(
            "Skipping remote context cache cleanup: Gemini client unavailable",
            exc_info=True,
        )
        _registry.clear()
        logger.info("Cleared 0 context cache(s) (registry only)")
        return 0

    for key, name in list(_registry.items()):
        try:
            await client.aio.caches.delete(name=name)
            count += 1
        except Exception:
            pass
    _registry.clear()
    logger.info("Cleared %d context cache(s)", count)
    return count
