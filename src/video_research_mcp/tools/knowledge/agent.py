"""knowledge_ask and knowledge_query tools — QueryAgent-powered retrieval.

Uses weaviate-agents QueryAgent for AI-powered question answering (ask mode)
and natural language object retrieval (search mode) across knowledge collections.
Requires the optional `weaviate-agents` package.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

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
from .helpers import ALL_COLLECTION_NAMES, serialize

logger = logging.getLogger(__name__)

try:
    from weaviate.agents.query import QueryAgent

    _HAS_QUERY_AGENT = True
except (ImportError, Exception):
    # weaviate-client raises WeaviateAgentsNotInstalledError (not an ImportError)
    # when the weaviate-agents extra is missing
    _HAS_QUERY_AGENT = False

_query_agents: dict[tuple[str, ...], QueryAgent] = {}
_agent_lock = threading.Lock()

_MISSING_DEP_ERROR = (
    "weaviate-agents not installed. Run: uv pip install 'video-research-mcp[agents]'"
)


def _get_query_agent(collections: list[str] | None = None) -> QueryAgent:
    """Return a cached QueryAgent for the given collection set."""
    target = tuple(sorted(collections)) if collections else tuple(ALL_COLLECTION_NAMES)
    with _agent_lock:
        if target not in _query_agents:
            client = WeaviateClient.get()
            _query_agents[target] = QueryAgent(client=client, collections=list(target))
        return _query_agents[target]


def _weaviate_not_configured() -> dict:
    """Return an empty result when Weaviate is not configured."""
    return {"error": "Weaviate not configured", "hint": "Set WEAVIATE_URL to enable knowledge tools"}


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def knowledge_ask(
    query: Annotated[str, Field(min_length=1, description="Question to answer from stored knowledge")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search (all if omitted)"),
    ] = None,
) -> dict:
    """Ask a question and get an AI-generated answer grounded in stored knowledge.

    Uses Weaviate QueryAgent in ask mode to synthesize an answer from
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
        return _weaviate_not_configured()

    try:
        target = list(collections) if collections else None

        def _ask():
            agent = _get_query_agent(target)
            return agent.ask(query)

        response = await asyncio.to_thread(_ask)

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
        ).model_dump()

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
async def knowledge_query(
    query: Annotated[str, Field(min_length=1, description="Natural language search query")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search (all if omitted)"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Max results")] = 10,
) -> dict:
    """Search knowledge store using natural language with automatic query understanding.

    Uses Weaviate QueryAgent in search mode for intelligent object retrieval.
    Returns raw objects like knowledge_search but with AI-powered query interpretation.

    Args:
        query: Natural language search query.
        collections: Which collections to search (default: all).
        limit: Maximum number of results.

    Returns:
        Dict matching KnowledgeQueryResult schema, or error dict.
    """
    if not _HAS_QUERY_AGENT:
        return make_tool_error(ImportError(_MISSING_DEP_ERROR))
    if not get_config().weaviate_enabled:
        return _weaviate_not_configured()

    try:
        target = list(collections) if collections else None

        def _search():
            agent = _get_query_agent(target)
            return agent.search(query, limit=limit)

        response = await asyncio.to_thread(_search)

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

        return KnowledgeQueryResult(
            query=query, total_results=len(hits), results=hits,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)
