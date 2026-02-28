"""Auto-load environment variables from a shared config file.

Reuses the same config path as video-research-mcp so users configure
API keys once in ``~/.config/video-research-mcp/.env``.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path.home() / ".config" / "video-research-mcp" / ".env"


def _is_unset_or_placeholder(key: str, value: str | None) -> bool:
    """Return True when the current env value should be treated as unset.

    Accepts blank/whitespace values and unresolved self-placeholders that
    some MCP hosts may pass through unchanged (e.g. ``${EXPLAINER_PATH}``).
    """
    if value is None:
        return True

    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in ('"', "'"):
        normalized = normalized[1:-1].strip()
    if not normalized:
        return True

    if normalized in {f"${key}", f"${{{key}}}"}:
        return True
    return normalized.startswith(f"${{{key}:-") and normalized.endswith("}")


def parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file into a dict of key-value pairs.

    Args:
        path: Path to the ``.env`` file.

    Returns:
        Dict mapping variable names to their string values.
    """
    result: dict[str, str] = {}
    if not path.is_file():
        return result

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load vars from *path* into ``os.environ`` when existing values are unset.

    Args:
        path: Path to the ``.env`` file. Defaults to :data:`DEFAULT_ENV_PATH`.

    Returns:
        Dict of vars that were actually injected.
    """
    if path is None:
        path = DEFAULT_ENV_PATH
    parsed = parse_dotenv(path)
    injected: dict[str, str] = {}
    for key, value in parsed.items():
        if _is_unset_or_placeholder(key, os.environ.get(key)):
            os.environ[key] = value
            injected[key] = value
    return injected
