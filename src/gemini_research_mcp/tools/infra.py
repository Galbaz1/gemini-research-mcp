"""Infrastructure tools — 2 tools on a FastMCP sub-server."""

from __future__ import annotations

from fastmcp import FastMCP

from .. import cache as cache_mod
from ..config import update_config

infra_server = FastMCP("infra")


@infra_server.tool()
async def infra_cache(
    action: str = "stats",
    content_id: str | None = None,
) -> dict:
    """Manage the analysis cache — stats / list / clear.

    Actions:
      stats  — file count, size, TTL
      list   — all cached entries with metadata
      clear  — remove all (or just *content_id*) cache files
    """
    if action == "stats":
        return cache_mod.stats()
    if action == "list":
        return {"entries": cache_mod.list_entries()}
    if action == "clear":
        removed = cache_mod.clear(content_id)
        return {"removed": removed}
    return {"error": f"Unknown action: {action}", "valid_actions": ["stats", "list", "clear"]}


@infra_server.tool()
async def infra_configure(
    model: str | None = None,
    thinking_level: str | None = None,
    temperature: float | None = None,
) -> dict:
    """Reconfigure the server at runtime (model, thinking level, temperature).

    Changes take effect immediately — no restart needed.
    """
    cfg = update_config(
        default_model=model,
        default_thinking_level=thinking_level,
        default_temperature=temperature,
    )
    return {"current_config": cfg.model_dump(exclude={"gemini_api_key"})}
