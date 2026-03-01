"""knowledge_ask and knowledge_query tools — AsyncQueryAgent-powered retrieval.

Uses weaviate-agents AsyncQueryAgent for AI-powered question answering (ask mode)
and natural language object retrieval (search mode) across knowledge collections.
Requires the optional `weaviate-agents` package.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from ...tracing import trace

from ...config import get_config
from ...errors import make_tool_error
from ...models.knowledge import (
    KnowledgeAskResult,
    KnowledgeAskSource,
    KnowledgeHit,
    KnowledgeQueryResult,
)
from ...types import KnowledgeCollection
from ...weaviate_client import WeaviateClient
from . import knowledge_server
from .helpers import ALL_COLLECTION_NAMES, serialize, weaviate_not_configured

logger = logging.getLogger(__name__)

try:
    from weaviate.agents.query import AsyncQueryAgent

    _HAS_QUERY_AGENT = True
except (ImportError, Exception):
    # weaviate-client raises WeaviateAgentsNotInstalledError (not an ImportError)
    # when the weaviate-agents extra is missing
    _HAS_QUERY_AGENT = False

_query_agents: dict[tuple[str, ...], tuple[object, AsyncQueryAgent]] = {}
_agent_lock = asyncio.Lock()

_MISSING_DEP_ERROR = (
    "weaviate-agents not installed. Run: uv pip install 'video-research-mcp[agents]'"
)


async def _get_query_agent(collections: list[str] | None = None) -> AsyncQueryAgent:
    """Return a cached AsyncQueryAgent, invalidating on client reconnect."""
    target = tuple(sorted(collections)) if collections else tuple(ALL_COLLECTION_NAMES)
    client = await WeaviateClient.aget()
    async with _agent_lock:
        cached = _query_agents.get(target)
        if cached is None or cached[0] is not client:
            agent = AsyncQueryAgent(client=client, collections=list(target))
            _query_agents[target] = (client, agent)
            return agent
        return cached[1]


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
@trace(name="knowledge_ask", span_type="TOOL")
async def knowledge_ask(
    query: Annotated[str, Field(min_length=1, description="Question to answer from stored knowledge")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search (all if omitted)"),
    ] = None,
) -> dict:
    """Ask a question and get an AI-generated answer grounded in stored knowledge.

    Uses Weaviate AsyncQueryAgent in ask mode to synthesize an answer from
    objects across knowledge collections, with source citations.

    Args:
        query: Natural language question.
        collections: Which collections to search (default: all).

    Returns:
        Dict matching KnowledgeAskResult schema, or error dict.
    """
    if not _HAS_QUERY_AGENT:
        return make_tool_error(ImportError(_MISSING_DEP_ERROR))
    if not get_config().weaviate_enabled:
        return weaviate_not_configured()

    try:
        target = list(collections) if collections else None
        agent = await _get_query_agent(target)
        response = await agent.ask(query)

        answer = getattr(response, "final_answer", "") or ""
        sources = [
            KnowledgeAskSource(
                collection=getattr(s, "collection", ""),
                object_id=str(getattr(s, "object_id", "")),
            )
            for s in getattr(response, "sources", []) or []
        ]

        return KnowledgeAskResult(
            query=query, answer=answer, sources=sources,
        ).model_dump(mode="json")

    except Exception as exc:
        return make_tool_error(exc)


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
@trace(name="knowledge_query", span_type="TOOL")
async def knowledge_query(
    query: Annotated[str, Field(min_length=1, description="Natural language search query")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search (all if omitted)"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Max results")] = 10,
) -> dict:
    """[DEPRECATED] Search knowledge store using natural language.

    Deprecated: Use knowledge_search instead, which now includes Cohere reranking
    and Flash summarization for better results with lower token usage.

    Uses Weaviate AsyncQueryAgent in search mode for intelligent object retrieval.

    Args:
        query: Natural language search query.
        collections: Which collections to search (default: all).
        limit: Maximum number of results.

    Returns:
        Dict matching KnowledgeQueryResult schema, or error dict.
    """
    logger.warning("knowledge_query is deprecated — use knowledge_search instead")
    if not _HAS_QUERY_AGENT:
        return make_tool_error(ImportError(_MISSING_DEP_ERROR))
    if not get_config().weaviate_enabled:
        return weaviate_not_configured()

    try:
        target = list(collections) if collections else None
        agent = await _get_query_agent(target)
        response = await agent.search(query, limit=limit)

        results = getattr(response, "search_results", None)
        objects = getattr(results, "objects", []) or []

        hits = []
        for obj in objects:
            props = {k: serialize(v) for k, v in getattr(obj, "properties", {}).items()}
            collection = getattr(obj, "collection", "")
            object_id = str(getattr(obj, "uuid", ""))
            hits.append(KnowledgeHit(
                collection=collection, object_id=object_id, properties=props,
            ))

        result = KnowledgeQueryResult(
            query=query, total_results=len(hits), results=hits,
        ).model_dump(mode="json")
        result["_deprecated"] = True
        result["_deprecation_notice"] = (
            "knowledge_query is deprecated. Use knowledge_search instead, "
            "which now includes Cohere reranking and Flash summarization."
        )
        return result

    except Exception as exc:
        return make_tool_error(exc)
