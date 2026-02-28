"""Shared utilities for Weaviate store functions.

Provides the enabled guard, timestamp helper, and logger used
by all domain-specific store modules.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import get_config

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    """Guard — returns False if Weaviate is not configured."""
    return get_config().weaviate_enabled


def _now() -> datetime:
    """Return current UTC datetime (Weaviate accepts datetime objects directly)."""
    return datetime.now(timezone.utc)
