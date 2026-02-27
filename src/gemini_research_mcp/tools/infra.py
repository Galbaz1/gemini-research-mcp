"""Infrastructure tools — 2 tools on a FastMCP sub-server."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .. import cache as cache_mod
from ..config import update_config
from ..errors import make_tool_error
from ..types import CacheAction, ThinkingLevel

infra_server = FastMCP("infra")


@infra_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def infra_cache(
    action: CacheAction = "stats",
    content_id: Annotated[str | None, Field(description="Scope clear to a specific content ID")] = None,
) -> dict:
    """Manage the analysis cache — stats, list, or clear entries.

    Args:
        action: Cache operation — "stats", "list", or "clear".
        content_id: When action is "clear", limit deletion to this content ID.

    Returns:
        Dict with operation-specific results (file_count, entries, or removed count).
    """
    if action == "stats":
        return cache_mod.stats()
    if action == "list":
        return {"entries": cache_mod.list_entries()}
    if action == "clear":
        removed = cache_mod.clear(content_id)
        return {"removed": removed}
    return {"error": f"Unknown action: {action}", "valid_actions": ["stats", "list", "clear"]}


@infra_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def infra_configure(
    model: Annotated[str | None, Field(description="Gemini model ID to use")] = None,
    thinking_level: ThinkingLevel | None = None,
    temperature: Annotated[float | None, Field(ge=0.0, le=2.0, description="Sampling temperature")] = None,
) -> dict:
    """Reconfigure the server at runtime — model, thinking level, or temperature.

    Changes take effect immediately for all subsequent tool calls.

    Args:
        model: Gemini model ID (e.g. "gemini-3.1-pro-preview").
        thinking_level: Thinking depth — "minimal", "low", "medium", or "high".
        temperature: Sampling temperature (0.0–2.0).

    Returns:
        Dict with current_config reflecting the updated settings.
    """
    try:
        cfg = update_config(
            default_model=model,
            default_thinking_level=thinking_level,
            default_temperature=temperature,
        )
        return {"current_config": cfg.model_dump(exclude={"gemini_api_key"})}
    except Exception as exc:
        return make_tool_error(exc)
