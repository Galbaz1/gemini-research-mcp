"""knowledge_ingest tool — manual data insertion into Weaviate collections."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from ...config import get_config
from ...errors import make_tool_error
from ...models.knowledge import KnowledgeIngestResult
from ...types import KnowledgeCollection
from ...weaviate_client import WeaviateClient
from . import knowledge_server
from .helpers import ALLOWED_PROPERTIES, weaviate_not_configured
from ...tracing import trace


@knowledge_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )
)
@trace(name="knowledge_ingest", span_type="TOOL")
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
        return weaviate_not_configured()

    # MCP JSON-RPC transport may serialize dict params as JSON strings
    if isinstance(properties, str):
        try:
            parsed = json.loads(properties)
            if isinstance(parsed, dict):
                properties = parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # Validate properties against schema
    allowed = ALLOWED_PROPERTIES.get(collection, set())
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
