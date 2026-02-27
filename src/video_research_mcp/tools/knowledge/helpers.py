"""Shared helpers and constants for knowledge tools."""

from __future__ import annotations

import logging
from typing import Literal

from ...weaviate_schema import ALL_COLLECTIONS as SCHEMA_COLLECTIONS

SearchType = Literal["hybrid", "semantic", "keyword"]

logger = logging.getLogger(__name__)

ALL_COLLECTION_NAMES: list[str] = [c.name for c in SCHEMA_COLLECTIONS]

# Pre-compute allowed property names per collection for ingest validation
ALLOWED_PROPERTIES: dict[str, set[str]] = {
    c.name: {p.name for p in c.properties} for c in SCHEMA_COLLECTIONS
}


def weaviate_not_configured() -> dict:
    """Return an empty result when Weaviate is not configured."""
    return {"error": "Weaviate not configured", "hint": "Set WEAVIATE_URL to enable knowledge tools"}


def serialize(value: object) -> object:
    """Make Weaviate property values JSON-serializable."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value
