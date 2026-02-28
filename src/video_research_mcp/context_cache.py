"""Process-scoped registry for Gemini context caches.

Maps (content_id, model) → cache_name. All operations are best-effort;
failures return None/False and never raise.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from google.genai import types

from .client import GeminiClient
from .config import get_config

logger = logging.getLogger(__name__)

_registry: dict[tuple[str, str], str] = {}
_pending: dict[tuple[str, str], asyncio.Task] = {}
_suppressed: set[tuple[str, str]] = set()  # (content_id, model) pairs that failed min-token check
_loaded: bool = False
_MAX_REGISTRY_ENTRIES = 200


def _registry_path() -> Path:
    """Path to the JSON registry sidecar file."""
    return Path(get_config().cache_dir) / "context_cache_registry.json"


def _save_registry() -> None:
    """Serialize registry to disk. Caps at _MAX_REGISTRY_ENTRIES (oldest evicted). Best-effort."""
    try:
        while len(_registry) > _MAX_REGISTRY_ENTRIES:
            _registry.pop(next(iter(_registry)))
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        nested: dict[str, dict[str, str]] = {}
        for (cid, model), name in _registry.items():
            nested.setdefault(cid, {})[model] = name
        # Atomic write: tmp file + rename prevents corruption on crash
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(nested))
        tmp.replace(path)
    except Exception:
        logger.debug("Failed to save context cache registry", exc_info=True)


def _load_registry() -> None:
    """Load registry from disk on first access. Best-effort — falls back to empty."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        path = _registry_path()
        if not path.exists():
            return
        nested = json.loads(path.read_text())
        for cid, models in nested.items():
            for model, name in models.items():
                _registry.setdefault((cid, model), name)
    except Exception:
        logger.debug("Failed to load context cache registry", exc_info=True)


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
    _load_registry()
    key = (content_id, model)

    if key in _suppressed:
        logger.debug("Skipping cache for %s/%s (suppressed: too few tokens)", content_id, model)
        return None

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
            _save_registry()  # persist eviction even if recreate fails

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
            _save_registry()
            logger.info(
                "Created context cache %s for %s (model=%s, ttl=%s)",
                cached.name, content_id, model, ttl,
            )
            return cached.name
    except Exception as exc:
        msg = str(exc).lower()
        if "too few tokens" in msg or "minimum" in msg:
            _suppressed.add(key)
            logger.info("Suppressing future cache attempts for %s/%s (too few tokens)", content_id, model)
        else:
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
    _load_registry()
    return _registry.get((content_id, model))


def start_prewarm(
    content_id: str,
    video_parts: list[types.Part],
    model: str,
) -> asyncio.Task:
    """Start a background prewarm, tracking it for later await.

    Args:
        content_id: Stable identifier (YouTube video_id or file hash).
        video_parts: The video Part(s) to cache.
        model: Model ID the cache will be used with.

    Returns:
        The background Task (also tracked in _pending).
    """
    key = (content_id, model)
    existing = _pending.get(key)
    if existing and not existing.done():
        return existing
    task = asyncio.create_task(get_or_create(content_id, video_parts, model))
    _pending[key] = task
    task.add_done_callback(lambda t: _pending.pop(key, None) if _pending.get(key) is t else None)
    return task


async def lookup_or_await(
    content_id: str, model: str, timeout: float = 5.0
) -> str | None:
    """Registry lookup, falling back to bounded await of a pending prewarm.

    Args:
        content_id: Stable identifier.
        model: Model ID to look up.
        timeout: Max seconds to wait for a pending prewarm task.

    Returns:
        Cache resource name or None.
    """
    name = lookup(content_id, model)
    if name:
        return name
    task = _pending.get((content_id, model))
    if task:
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout)
        except (asyncio.TimeoutError, Exception):
            return None
    return None


async def clear() -> int:
    """Delete all tracked caches and clear the registry. Returns count cleared."""
    _load_registry()
    _suppressed.clear()
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
        _suppressed.clear()
        _save_registry()
        logger.info("Cleared 0 context cache(s) (registry only)")
        return 0

    for key, name in list(_registry.items()):
        try:
            await client.aio.caches.delete(name=name)
            count += 1
        except Exception:
            pass
    _registry.clear()
    _suppressed.clear()
    _save_registry()
    logger.info("Cleared %d context cache(s)", count)
    return count
