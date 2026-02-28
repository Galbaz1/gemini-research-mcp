"""Store function for CommunityReactions collection."""

from __future__ import annotations

import asyncio
import json

import weaviate.util

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_community_reaction(reaction: dict) -> str | None:
    """Persist a community reaction analysis to CommunityReactions.

    Uses a deterministic UUID derived from video_id so repeated analyses
    of the same video upsert rather than duplicate.

    Args:
        reaction: Dict with video_id, video_title, sentiment_*, themes_*,
                  consensus, notable_opinions, and comment_count.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _upsert():
            client = WeaviateClient.get()
            collection = client.collections.get("CommunityReactions")
            video_id = reaction.get("video_id", "")
            props = {
                "created_at": _now(),
                "source_tool": reaction.get("source_tool", "comment_analyst"),
                "video_id": video_id,
                "video_title": reaction.get("video_title", ""),
                "comment_count": reaction.get("comment_count", 0),
                "sentiment_positive": reaction.get("sentiment_positive", 0.0),
                "sentiment_negative": reaction.get("sentiment_negative", 0.0),
                "sentiment_neutral": reaction.get("sentiment_neutral", 0.0),
                "themes_positive": reaction.get("themes_positive", []),
                "themes_critical": reaction.get("themes_critical", []),
                "consensus": reaction.get("consensus", ""),
                "notable_opinions_json": json.dumps(reaction.get("notable_opinions", [])),
            }

            if video_id:
                det_uuid = weaviate.util.generate_uuid5(f"community:{video_id}")
                try:
                    collection.data.replace(uuid=det_uuid, properties=props)
                    return str(det_uuid)
                except Exception:
                    uuid = str(collection.data.insert(properties=props, uuid=det_uuid))
                    # Cross-ref to VideoMetadata (non-fatal)
                    try:
                        meta_uuid = weaviate.util.generate_uuid5(video_id)
                        collection.data.reference_add(
                            from_uuid=det_uuid, from_property="for_video", to=meta_uuid,
                        )
                    except Exception:
                        pass
                    return uuid

            return str(collection.data.insert(properties=props))

        return await asyncio.to_thread(_upsert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
