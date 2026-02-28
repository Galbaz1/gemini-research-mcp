"""Store function for CallNotes collection."""

from __future__ import annotations

import asyncio

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_call_notes(notes: dict) -> str | None:
    """Persist meeting/call notes to the CallNotes collection.

    Args:
        notes: Dict with video_id, source_url, title, summary,
               participants, decisions, action_items, topics_discussed,
               duration, meeting_date.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("CallNotes")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": notes.get("source_tool", "video_analyze"),
                "video_id": notes.get("video_id", ""),
                "source_url": notes.get("source_url", ""),
                "title": notes.get("title", ""),
                "summary": notes.get("summary", ""),
                "participants": notes.get("participants", []),
                "decisions": notes.get("decisions", []),
                "action_items": notes.get("action_items", []),
                "topics_discussed": notes.get("topics_discussed", []),
                "duration": notes.get("duration", ""),
                "meeting_date": notes.get("meeting_date", ""),
                "local_filepath": notes.get("local_filepath", ""),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
