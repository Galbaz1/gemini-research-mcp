"""knowledge_search tool — hybrid, semantic, and keyword search across collections."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field
from weaviate.classes.query import MetadataQuery

from ...config import get_config
from ...errors import make_tool_error
from ...models.knowledge import KnowledgeHit, KnowledgeSearchResult
from ...types import KnowledgeCollection
from ...weaviate_client import WeaviateClient
from ..knowledge_filters import build_collection_filter
from . import knowledge_server
from .helpers import ALL_COLLECTION_NAMES, ALLOWED_PROPERTIES, SearchType, logger, serialize
from ...tracing import trace


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
@trace(name="knowledge_search", span_type="TOOL")
async def knowledge_search(
    query: Annotated[str, Field(min_length=1, description="Search query")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search (all if omitted)"),
    ] = None,
    search_type: Annotated[
        SearchType,
        Field(description="Search mode: hybrid (BM25+vector), semantic (vector only), keyword (BM25 only)"),
    ] = "hybrid",
    limit: Annotated[int, Field(ge=1, le=100, description="Max results per collection")] = 10,
    alpha: Annotated[float, Field(ge=0.0, le=1.0, description="Hybrid balance: 0=BM25, 1=vector")] = 0.5,
    evidence_tier: Annotated[str | None, Field(description="Filter by evidence tier (e.g. CONFIRMED)")] = None,
    source_tool: Annotated[str | None, Field(description="Filter by originating tool name")] = None,
    date_from: Annotated[str | None, Field(description="Filter created_at >= ISO date")] = None,
    date_to: Annotated[str | None, Field(description="Filter created_at <= ISO date")] = None,
    category: Annotated[str | None, Field(description="Filter VideoMetadata by category")] = None,
    video_id: Annotated[str | None, Field(description="Filter by video_id")] = None,
) -> dict:
    """Search across knowledge collections using hybrid, semantic, or keyword mode.

    Searches any/all 7 collections. Results are merged and sorted by score.
    Filters are collection-aware: conditions are skipped for collections
    that lack the relevant property.

    Args:
        query: Text to search for.
        collections: Which collections to search (default: all).
        search_type: Search algorithm — hybrid, semantic (near_text), or keyword (BM25).
        limit: Maximum results per collection.
        alpha: Hybrid balance (only used when search_type="hybrid").
        evidence_tier: Filter ResearchFindings by evidence tier.
        source_tool: Filter any collection by originating tool.
        date_from: Filter objects created on or after this ISO date.
        date_to: Filter objects created on or before this ISO date.
        category: Filter VideoMetadata by category label.
        video_id: Filter by video_id field.

    Returns:
        Dict matching KnowledgeSearchResult schema.
    """
    if not get_config().weaviate_enabled:
        return KnowledgeSearchResult(query=query).model_dump()

    try:
        target = list(collections) if collections else ALL_COLLECTION_NAMES
        filter_kwargs = dict(
            evidence_tier=evidence_tier, source_tool=source_tool,
            date_from=date_from, date_to=date_to,
            category=category, video_id=video_id,
        )
        filters_applied = {k: v for k, v in filter_kwargs.items() if v is not None} or None

        def _search():
            client = WeaviateClient.get()
            hits: list[KnowledgeHit] = []
            for col_name in target:
                try:
                    collection = client.collections.get(col_name)
                    col_filter = build_collection_filter(
                        col_name, ALLOWED_PROPERTIES.get(col_name, set()), **filter_kwargs,
                    )
                    response = _dispatch_search(
                        collection, query, search_type, limit, alpha, col_filter,
                    )
                    for obj in response.objects:
                        props = {k: serialize(v) for k, v in obj.properties.items()}
                        hits.append(KnowledgeHit(
                            collection=col_name,
                            object_id=str(obj.uuid),
                            score=_extract_score(obj, search_type),
                            properties=props,
                        ))
                except Exception as exc:
                    logger.warning("Search failed for %s: %s", col_name, exc)

            hits.sort(key=lambda h: h.score, reverse=True)
            return hits

        hits = await asyncio.to_thread(_search)
        return KnowledgeSearchResult(
            query=query,
            total_results=len(hits),
            results=hits,
            filters_applied=filters_applied,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


def _dispatch_search(collection, query, search_type, limit, alpha, col_filter):
    """Dispatch to the correct Weaviate query method based on search_type."""
    if search_type == "semantic":
        return collection.query.near_text(
            query=query,
            limit=limit,
            filters=col_filter,
            return_metadata=MetadataQuery(distance=True),
        )
    if search_type == "keyword":
        return collection.query.bm25(
            query=query,
            limit=limit,
            filters=col_filter,
            return_metadata=MetadataQuery(score=True),
        )
    # Default: hybrid
    return collection.query.hybrid(
        query=query,
        limit=limit,
        alpha=alpha,
        filters=col_filter,
        return_metadata=MetadataQuery(score=True),
    )


def _extract_score(obj, search_type: str) -> float:
    """Extract a normalized score from a Weaviate result object."""
    if search_type == "semantic":
        distance = getattr(obj.metadata, "distance", None)
        return 1.0 - distance if distance is not None else 0.0
    return getattr(obj.metadata, "score", 0.0) or 0.0
