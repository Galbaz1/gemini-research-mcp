"""Store functions for ConceptKnowledge and RelationshipEdges collections."""

from __future__ import annotations

import asyncio

import weaviate.util
from weaviate.classes.data import DataObject

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_concept_knowledge(concept: dict) -> str | None:
    """Persist a concept to ConceptKnowledge.

    Uses a deterministic UUID derived from source_url + concept_name
    so the same concept from the same source upserts rather than duplicates.

    Args:
        concept: Dict with concept_name, state, source_url, source_title,
                 source_category, description, timestamp.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _upsert():
            client = WeaviateClient.get()
            collection = client.collections.get("ConceptKnowledge")
            source_url = concept.get("source_url", "")
            concept_name = concept.get("concept_name", "")
            props = {
                "created_at": _now(),
                "source_tool": concept.get("source_tool", "video_analyze"),
                "concept_name": concept_name,
                "state": concept.get("state", "unknown"),
                "source_url": source_url,
                "source_title": concept.get("source_title", ""),
                "source_category": concept.get("source_category", ""),
                "description": concept.get("description", ""),
                "timestamp": concept.get("timestamp", ""),
            }

            if source_url and concept_name:
                det_uuid = weaviate.util.generate_uuid5(f"{source_url}:{concept_name}")
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


async def store_relationship_edges(edges: list[dict]) -> list[str] | None:
    """Persist relationship edges to RelationshipEdges via batch insert.

    Args:
        edges: List of dicts with from_concept, to_concept,
               relationship_type, source_url, source_category.

    Returns:
        List of Weaviate object UUIDs, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    if not edges:
        return []
    try:
        def _batch_insert():
            client = WeaviateClient.get()
            collection = client.collections.get("RelationshipEdges")
            now = _now()
            objects = [
                DataObject(properties={
                    "created_at": now,
                    "source_tool": edge.get("source_tool", "video_analyze"),
                    "from_concept": edge.get("from_concept", ""),
                    "to_concept": edge.get("to_concept", ""),
                    "relationship_type": edge.get("relationship_type", "related_to"),
                    "source_url": edge.get("source_url", ""),
                    "source_category": edge.get("source_category", ""),
                })
                for edge in edges
            ]
            result = collection.data.insert_many(objects)
            return [str(obj.uuid) for obj in result.all_objects]

        return await asyncio.to_thread(_batch_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
