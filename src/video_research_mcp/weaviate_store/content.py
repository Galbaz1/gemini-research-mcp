"""Store function for ContentAnalyses collection."""

from __future__ import annotations

import asyncio
import json

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_content_analysis(
    result: dict, source: str, instruction: str
) -> str | None:
    """Persist a content_analyze result to the ContentAnalyses collection.

    Args:
        result: Serialised ContentResult dict.
        source: URL, file path, or "(text)" for inline text input.
        instruction: The analysis instruction used.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("ContentAnalyses")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "content_analyze",
                "source": source,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "entities": result.get("entities", []),
                "raw_result": json.dumps(result),
                "structure_notes": result.get("structure_notes", ""),
                "quality_assessment": result.get("quality_assessment", ""),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
