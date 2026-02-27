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
from weaviate.classes.init import Auth

from .config import get_config

logger = logging.getLogger(__name__)

_client: weaviate.WeaviateClient | None = None
_schema_ensured = False
_lock = threading.Lock()


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
        )

    if parsed.scheme == "https":
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=Auth.api_key(api_key) if api_key else None,
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
        """Idempotent schema creation — skips existing collections."""
        from .weaviate_schema import ALL_COLLECTIONS

        if _client is None:
            return

        existing = set(_client.collections.list_all().keys())
        for col_def in ALL_COLLECTIONS:
            if col_def.name not in existing:
                _client.collections.create_from_dict(col_def.to_dict())
                logger.info("Created Weaviate collection: %s", col_def.name)
            else:
                logger.debug("Collection already exists: %s", col_def.name)

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
