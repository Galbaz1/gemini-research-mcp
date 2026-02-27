"""Weaviate client singleton — mirrors GeminiClient pattern from client.py.

Provides a process-wide WeaviateClient that lazily connects on first use
and idempotently creates collections from weaviate_schema.ALL_COLLECTIONS.
Used by weaviate_store.py (write-through) and tools/knowledge.py (queries).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from urllib.parse import urlparse

import weaviate
from weaviate.classes.config import Configure, DataType, Property, ReferenceProperty
from weaviate.classes.init import AdditionalConfig, Auth, Timeout

from .config import get_config
from .weaviate_schema import CollectionDef, PropertyDef

logger = logging.getLogger(__name__)

_client: weaviate.WeaviateClient | None = None
_schema_ensured = False
_lock = threading.Lock()

_DATA_TYPE_MAP: dict[str, DataType] = {
    "text": DataType.TEXT,
    "text[]": DataType.TEXT_ARRAY,
    "int": DataType.INT,
    "number": DataType.NUMBER,
    "boolean": DataType.BOOL,
    "date": DataType.DATE,
}


def _resolve_data_type(type_str: str) -> DataType:
    """Map a schema string type name to a Weaviate DataType enum value."""
    dt = _DATA_TYPE_MAP.get(type_str)
    if dt is None:
        raise ValueError(f"Unknown data type: {type_str!r}")
    return dt


def _to_property(prop_def: PropertyDef) -> Property:
    """Convert a PropertyDef to a v4 Property object with full index config."""
    kwargs: dict = {
        "name": prop_def.name,
        "data_type": _resolve_data_type(prop_def.data_type[0]),
        "description": prop_def.description or None,
        "skip_vectorization": prop_def.skip_vectorization,
        "index_filterable": prop_def.index_filterable,
        "index_range_filters": prop_def.index_range_filters,
    }
    if prop_def.index_searchable is not None:
        kwargs["index_searchable"] = prop_def.index_searchable
    return Property(**kwargs)


_TIMEOUT = Timeout(init=30, query=60, insert=120)
_ADDITIONAL_CONFIG = AdditionalConfig(timeout=_TIMEOUT)


def _connect(url: str, api_key: str) -> weaviate.WeaviateClient:
    """Connect to Weaviate using the appropriate method for the URL scheme.

    Supports:
        - WCS cloud clusters (https://*.weaviate.network, etc.)
        - Local instances (http://localhost:*, http://127.0.0.1:*)
        - Custom deployments (any other URL)
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    is_local = host in ("localhost", "127.0.0.1", "::1") or host.startswith("192.168.")

    if is_local:
        port = parsed.port or 8080
        grpc_port = port + 1  # convention: gRPC on HTTP port + 1
        return weaviate.connect_to_local(
            host=host,
            port=port,
            grpc_port=grpc_port,
            additional_config=_ADDITIONAL_CONFIG,
        )

    if parsed.scheme == "https":
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=Auth.api_key(api_key) if api_key else None,
            additional_config=_ADDITIONAL_CONFIG,
        )

    # Custom deployment (non-local, non-WCS)
    return weaviate.connect_to_custom(
        http_host=host,
        http_port=parsed.port or 8080,
        http_secure=parsed.scheme == "https",
        grpc_host=host,
        grpc_port=(parsed.port or 8080) + 1,
        grpc_secure=parsed.scheme == "https",
        auth_credentials=Auth.api_key(api_key) if api_key else None,
        additional_config=_ADDITIONAL_CONFIG,
    )


class WeaviateClient:
    """Process-wide Weaviate client singleton (single cluster, not a pool).

    All methods are classmethods operating on module-level _client state.
    Thread-safe via _lock for concurrent asyncio.to_thread usage.
    """

    @classmethod
    def get(cls) -> weaviate.WeaviateClient:
        """Return (or create) the shared Weaviate client.

        Thread-safe via threading.Lock — safe for concurrent asyncio.to_thread calls.

        Raises:
            ValueError: If WEAVIATE_URL is not configured.
            ConnectionError: If the cluster is unreachable.
        """
        global _client, _schema_ensured
        cfg = get_config()
        if not cfg.weaviate_url:
            raise ValueError("WEAVIATE_URL not configured")

        with _lock:
            if _client is None:
                _client = _connect(cfg.weaviate_url, cfg.weaviate_api_key)
                logger.info("Connected to Weaviate at %s", cfg.weaviate_url)

            if not _schema_ensured:
                cls.ensure_collections()
                _schema_ensured = True

        return _client

    @classmethod
    def ensure_collections(cls) -> None:
        """Idempotent schema creation + evolution for existing deployments.

        Pass 1: create missing collections, evolve existing ones.
        Pass 2: add cross-references (targets must exist first).
        """
        from .weaviate_schema import ALL_COLLECTIONS

        if _client is None:
            return

        existing = set(_client.collections.list_all().keys())
        for col_def in ALL_COLLECTIONS:
            if col_def.name not in existing:
                _client.collections.create(
                    name=col_def.name,
                    description=col_def.description,
                    properties=[_to_property(p) for p in col_def.properties],
                    vector_config=Configure.Vectors.text2vec_weaviate(),
                )
                logger.info("Created Weaviate collection: %s", col_def.name)
            else:
                cls._evolve_collection(col_def)

        cls._ensure_references(ALL_COLLECTIONS)

    @classmethod
    def _evolve_collection(cls, col_def: CollectionDef) -> None:
        """Add missing properties to an existing collection (additive only)."""
        col = _client.collections.get(col_def.name)
        existing_props = {p.name for p in col.config.get().properties}

        for prop_def in col_def.properties:
            if prop_def.name in existing_props:
                continue
            try:
                col.config.add_property(_to_property(prop_def))
                logger.info("Added property %s.%s", col_def.name, prop_def.name)
            except Exception as exc:
                logger.debug("Property %s.%s already exists or failed: %s", col_def.name, prop_def.name, exc)

    @classmethod
    def _ensure_references(cls, collections: list[CollectionDef]) -> None:
        """Add missing cross-references (second pass, targets must exist)."""
        for col_def in collections:
            if not col_def.references:
                continue
            col = _client.collections.get(col_def.name)
            for ref_def in col_def.references:
                try:
                    col.config.add_reference(ReferenceProperty(
                        name=ref_def.name,
                        target_collection=ref_def.target_collection,
                    ))
                    logger.info("Added reference %s.%s → %s", col_def.name, ref_def.name, ref_def.target_collection)
                except Exception as exc:
                    logger.debug("Reference %s.%s already exists or failed: %s", col_def.name, ref_def.name, exc)

    @classmethod
    def is_available(cls) -> bool:
        """Check if Weaviate is configured and reachable."""
        cfg = get_config()
        if not cfg.weaviate_enabled:
            return False
        try:
            cls.get()
            return _client is not None and _client.is_ready()
        except Exception:
            return False

    @classmethod
    def close(cls) -> None:
        """Close the shared client connection."""
        global _client, _schema_ensured
        with _lock:
            if _client is not None:
                try:
                    _client.close()
                except Exception:
                    pass
                _client = None
                _schema_ensured = False
                logger.info("Closed Weaviate client")

    @classmethod
    async def aclose(cls) -> None:
        """Async wrapper for close — runs in thread to avoid blocking."""
        await asyncio.to_thread(cls.close)

    @classmethod
    def reset(cls) -> None:
        """Reset singleton state (testing utility, matches YouTubeClient.reset)."""
        global _client, _schema_ensured
        _client = None
        _schema_ensured = False
