"""Cache bridge helpers for video tools — prewarm, lookup, and session caching."""

from __future__ import annotations

import logging

from google.genai import types

from .. import context_cache
from ..config import get_config

logger = logging.getLogger(__name__)


def prewarm_cache(content_id: str, video_url: str) -> None:
    """Fire background cache prewarm for a YouTube video.

    Args:
        content_id: YouTube video ID.
        video_url: Normalized YouTube URL for the file_data Part.
    """
    cfg = get_config()
    warm_parts = [types.Part(file_data=types.FileData(file_uri=video_url))]
    context_cache.start_prewarm(content_id, warm_parts, cfg.default_model)


async def resolve_session_cache(video_id: str) -> tuple[str, str]:
    """Look up pre-warmed cache for session creation.

    Args:
        video_id: YouTube video ID to look up.

    Returns:
        (cache_name, model) — both empty strings if no cache found.
    """
    try:
        cfg = get_config()
        cache_name = await context_cache.lookup_or_await(video_id, cfg.default_model) or ""
        if cache_name:
            return cache_name, cfg.default_model
    except Exception:
        pass
    return "", ""


async def prepare_cached_request(
    session, prompt: str
) -> tuple[bool, list[types.Content], dict]:
    """Prepare request contents and config for a cached/uncached session continuation.

    Checks cache TTL, builds user content (text-only when cached, video+text
    when uncached), and assembles the GenerateContentConfig kwargs.

    Args:
        session: The active VideoSession.
        prompt: User follow-up question.

    Returns:
        (use_cache, contents, config_kwargs) — ready for generate_content.
    """
    use_cache = False
    if session.cache_name:
        cache_alive = await context_cache.refresh_ttl(session.cache_name)
        if cache_alive:
            use_cache = True
        else:
            session.cache_name = ""

    if use_cache:
        user_parts = [types.Part(text=prompt)]
    else:
        user_parts = [
            types.Part(file_data=types.FileData(file_uri=session.url)),
            types.Part(text=prompt),
        ]
    user_content = types.Content(role="user", parts=user_parts)
    contents = list(session.history) + [user_content]

    cfg = get_config()
    config_kwargs: dict = {
        "thinking_config": types.ThinkingConfig(thinking_level="medium"),
    }
    if use_cache:
        config_kwargs["cached_content"] = session.cache_name

    model = session.model if use_cache and session.model else cfg.default_model
    config_kwargs["_model"] = model  # passed through for caller convenience

    return use_cache, contents, config_kwargs
