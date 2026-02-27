"""Knowledge query tools — 6 tools on a FastMCP sub-server."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from weaviate.classes.query import MetadataQuery

from ..config import get_config
from ..errors import make_tool_error
from .knowledge_filters import build_collection_filter
from ..models.knowledge import (
    CollectionStats,
    KnowledgeFetchResult,
    KnowledgeHit,
    KnowledgeIngestResult,
    KnowledgeRelatedResult,
    KnowledgeSearchResult,
    KnowledgeStatsResult,
)
from ..types import KnowledgeCollection
from ..weaviate_client import WeaviateClient
from ..weaviate_schema import ALL_COLLECTIONS as SCHEMA_COLLECTIONS

SearchType = Literal["hybrid", "semantic", "keyword"]

logger = logging.getLogger(__name__)
knowledge_server = FastMCP("knowledge")

ALL_COLLECTION_NAMES: list[str] = [c.name for c in SCHEMA_COLLECTIONS]

# Pre-compute allowed property names per collection for ingest validation
_ALLOWED_PROPERTIES: dict[str, set[str]] = {
    c.name: {p.name for p in c.properties} for c in SCHEMA_COLLECTIONS
}


def _weaviate_not_configured() -> dict:
    """Return an empty result when Weaviate is not configured."""
    return {"error": "Weaviate not configured", "hint": "Set WEAVIATE_URL to enable knowledge tools"}


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
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
                        col_name, _ALLOWED_PROPERTIES.get(col_name, set()), **filter_kwargs,
                    )
                    response = _dispatch_search(
                        collection, query, search_type, limit, alpha, col_filter,
                    )
                    for obj in response.objects:
                        props = {k: _serialize(v) for k, v in obj.properties.items()}
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


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def knowledge_related(
    object_id: Annotated[str, Field(min_length=1, description="UUID of the source object")],
    collection: KnowledgeCollection,
    limit: Annotated[int, Field(ge=1, le=50, description="Max related results")] = 5,
) -> dict:
    """Find semantically related objects using near-object vector search.

    Args:
        object_id: UUID of the source object.
        collection: Collection the source object belongs to.
        limit: Maximum number of related results.

    Returns:
        Dict matching KnowledgeRelatedResult schema.
    """
    if not get_config().weaviate_enabled:
        return KnowledgeRelatedResult(
            source_id=object_id, source_collection=collection,
        ).model_dump()

    try:
        def _search():
            client = WeaviateClient.get()
            col = client.collections.get(collection)
            response = col.query.near_object(
                near_object=object_id,
                limit=limit + 1,
                return_metadata=MetadataQuery(distance=True),
            )
            hits = []
            for obj in response.objects:
                if str(obj.uuid) == object_id:
                    continue
                props = {k: _serialize(v) for k, v in obj.properties.items()}
                distance = getattr(obj.metadata, "distance", None)
                score = 1.0 - distance if distance is not None else 0.0
                hits.append(KnowledgeHit(
                    collection=collection,
                    object_id=str(obj.uuid),
                    score=score,
                    properties=props,
                ))
            return hits[:limit]

        hits = await asyncio.to_thread(_search)
        return KnowledgeRelatedResult(
            source_id=object_id,
            source_collection=collection,
            related=hits,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def knowledge_stats(
    collection: Annotated[
        KnowledgeCollection | None,
        Field(description="Collection to count (all if omitted)"),
    ] = None,
    group_by: Annotated[
        str | None,
        Field(description="Group counts by a text property (e.g. evidence_tier, source_tool)"),
    ] = None,
) -> dict:
    """Get object counts per collection, optionally grouped by a property.

    Args:
        collection: Single collection name, or None for all collections.
        group_by: Text property name to group counts by.

    Returns:
        Dict matching KnowledgeStatsResult schema.
    """
    if not get_config().weaviate_enabled:
        return KnowledgeStatsResult().model_dump()

    try:
        target = [collection] if collection else ALL_COLLECTION_NAMES

        def _count():
            client = WeaviateClient.get()
            stats = []
            for col_name in target:
                try:
                    col = client.collections.get(col_name)
                    agg = col.aggregate.over_all(total_count=True)
                    groups = None
                    if group_by and group_by in _ALLOWED_PROPERTIES.get(col_name, set()):
                        groups = _aggregate_groups(col, group_by)
                    stats.append(CollectionStats(
                        name=col_name,
                        count=agg.total_count or 0,
                        groups=groups,
                    ))
                except Exception as exc:
                    logger.warning("Stats failed for %s: %s", col_name, exc)
                    stats.append(CollectionStats(name=col_name, count=0))
            return stats

        stats = await asyncio.to_thread(_count)
        total = sum(s.count for s in stats)
        return KnowledgeStatsResult(
            collections=stats,
            total_objects=total,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


def _aggregate_groups(col, group_by: str) -> dict[str, int]:
    """Aggregate counts grouped by a text property value."""
    try:
        from weaviate.classes.aggregate import GroupByAggregate
        response = col.aggregate.over_all(
            group_by=GroupByAggregate(prop=group_by),
            total_count=True,
        )
        groups: dict[str, int] = {}
        for group in response.groups:
            key = str(group.grouped_by.value) if group.grouped_by else "(empty)"
            groups[key] = group.total_count or 0
        return groups
    except Exception:
        return {}


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )
)
async def knowledge_ingest(
    collection: KnowledgeCollection,
    properties: Annotated[dict, Field(description="Object properties to insert")],
) -> dict:
    """Manually insert data into a knowledge collection.

    Properties are validated against the collection schema — unknown keys
    are rejected.

    Args:
        collection: Target collection name.
        properties: Dict of property values matching the collection schema.

    Returns:
        Dict matching KnowledgeIngestResult schema.
    """
    if not get_config().weaviate_enabled:
        return _weaviate_not_configured()

    # Validate properties against schema
    allowed = _ALLOWED_PROPERTIES.get(collection, set())
    unknown = set(properties) - allowed
    if unknown:
        return make_tool_error(
            ValueError(f"Unknown properties for {collection}: {sorted(unknown)}")
        )

    try:
        def _insert():
            client = WeaviateClient.get()
            col = client.collections.get(collection)
            uuid = col.data.insert(properties=properties)
            return str(uuid)

        object_id = await asyncio.to_thread(_insert)
        return KnowledgeIngestResult(
            collection=collection,
            object_id=object_id,
            status="success",
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def knowledge_fetch(
    object_id: Annotated[str, Field(min_length=1, description="Weaviate object UUID")],
    collection: KnowledgeCollection,
) -> dict:
    """Fetch a single object by UUID from a knowledge collection.

    Args:
        object_id: UUID of the object to retrieve.
        collection: Collection the object belongs to.

    Returns:
        Dict matching KnowledgeFetchResult schema.
    """
    if not get_config().weaviate_enabled:
        return _weaviate_not_configured()

    try:
        def _fetch():
            client = WeaviateClient.get()
            col = client.collections.get(collection)
            obj = col.query.fetch_object_by_id(object_id)
            if obj is None:
                return KnowledgeFetchResult(
                    collection=collection, object_id=object_id, found=False,
                )
            props = {k: _serialize(v) for k, v in obj.properties.items()}
            return KnowledgeFetchResult(
                collection=collection,
                object_id=str(obj.uuid),
                found=True,
                properties=props,
            )

        result = await asyncio.to_thread(_fetch)
        return result.model_dump()

    except Exception as exc:
        return make_tool_error(exc)


def _serialize(value: object) -> object:
    """Make Weaviate property values JSON-serializable."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value
