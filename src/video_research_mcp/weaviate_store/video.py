"""Store functions for VideoAnalyses and VideoMetadata collections."""

from __future__ import annotations

import asyncio
import hashlib
import json

import weaviate.util

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_video_analysis(
    result: dict, content_id: str, instruction: str, source_url: str = ""
) -> str | None:
    """Persist a video_analyze result to the VideoAnalyses collection.

    Uses a deterministic UUID when content_id is present so repeated
    analyses of the same video with the same instruction upsert rather
    than duplicate.

    Args:
        result: Serialised VideoResult dict.
        content_id: YouTube video ID or file content hash.
        instruction: The analysis instruction used.
        source_url: Original URL or file path.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoAnalyses")
            props = {
                "created_at": _now(),
                "source_tool": "video_analyze",
                "video_id": content_id,
                "source_url": source_url,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "raw_result": json.dumps(result),
                "timestamps_json": json.dumps(result.get("timestamps", [])),
                "topics": result.get("topics", []),
                "sentiment": result.get("sentiment", ""),
            }

            # Deterministic UUID for dedup when content_id is available
            if content_id:
                instruction_hash = hashlib.sha256(instruction.encode()).hexdigest()[:12]
                det_uuid = weaviate.util.generate_uuid5(f"analysis:{content_id}:{instruction_hash}")
                try:
                    collection.data.replace(uuid=det_uuid, properties=props)
                    return str(det_uuid)
                except Exception:
                    return str(collection.data.insert(properties=props, uuid=det_uuid))

            uuid = collection.data.insert(properties=props)
            # Cross-ref to VideoMetadata (non-fatal)
            if content_id:
                try:
                    meta_uuid = weaviate.util.generate_uuid5(content_id)
                    collection.data.reference_add(from_uuid=uuid, from_property="has_metadata", to=meta_uuid)
                except Exception:
                    pass
            return str(uuid)

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_video_metadata(meta_dict: dict) -> str | None:
    """Persist video_metadata result to the VideoMetadata collection.

    Uses a deterministic UUID derived from video_id so repeated fetches
    for the same video upsert (replace) rather than duplicate.

    Args:
        meta_dict: Serialised VideoMetadata dict.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _upsert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoMetadata")
            video_id = meta_dict.get("video_id", "")
            props = _meta_properties(meta_dict, video_id)

            if video_id:
                det_uuid = weaviate.util.generate_uuid5(video_id)
                try:
                    collection.data.replace(uuid=det_uuid, properties=props)
                    return str(det_uuid)
                except Exception:
                    return str(collection.data.insert(properties=props, uuid=det_uuid))

            return str(collection.data.insert(properties=props))

        return await asyncio.to_thread(_upsert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


def _meta_properties(meta_dict: dict, video_id: str) -> dict:
    """Build the Weaviate properties dict for a VideoMetadata insert/replace."""
    return {
        "created_at": _now(),
        "source_tool": "video_metadata",
        "video_id": video_id,
        "title": meta_dict.get("title", ""),
        "description": meta_dict.get("description", ""),
        "channel_title": meta_dict.get("channel_title", ""),
        "tags": meta_dict.get("tags", []),
        "view_count": meta_dict.get("view_count", 0),
        "like_count": meta_dict.get("like_count", 0),
        "duration": meta_dict.get("duration", ""),
        "published_at": meta_dict.get("published_at", ""),
        "channel_id": meta_dict.get("channel_id", ""),
        "comment_count": meta_dict.get("comment_count", 0),
        "duration_seconds": meta_dict.get("duration_seconds", 0),
        "category": meta_dict.get("category", ""),
        "definition": meta_dict.get("definition", ""),
        "has_captions": meta_dict.get("has_captions", False),
        "default_language": meta_dict.get("default_language", ""),
    }
