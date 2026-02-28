"""Store function for WebSearchResults collection."""

from __future__ import annotations

import asyncio
import json

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_web_search(
    query: str, response: str, sources: list[dict]
) -> str | None:
    """Persist a web_search result to the WebSearchResults collection.

    Args:
        query: The search query string.
        response: Gemini's grounded response text.
        sources: List of grounding source dicts (serialised to JSON).

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("WebSearchResults")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "web_search",
                "query": query,
                "response": response,
                "sources_json": json.dumps(sources),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
