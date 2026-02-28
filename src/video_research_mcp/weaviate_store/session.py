"""Store function for SessionTranscripts collection."""

from __future__ import annotations

import asyncio

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_session_turn(
    session_id: str,
    video_title: str,
    turn_index: int,
    prompt: str,
    response: str,
    local_filepath: str = "",
) -> str | None:
    """Persist a video_continue_session turn to SessionTranscripts.

    Args:
        session_id: The active session ID.
        video_title: Title of the video being discussed.
        turn_index: One-based turn number in the session.
        prompt: User's prompt for this turn.
        response: Model's response text.
        local_filepath: Local filesystem path to the session's video file.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("SessionTranscripts")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "video_continue_session",
                "session_id": session_id,
                "video_title": video_title,
                "turn_index": turn_index,
                "turn_prompt": prompt,
                "turn_response": response,
                "local_filepath": local_filepath,
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
