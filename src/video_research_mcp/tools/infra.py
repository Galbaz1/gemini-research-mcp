"""Infrastructure tools — 2 tools on a FastMCP sub-server."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .. import cache as cache_mod
from ..config import MODEL_PRESETS, update_config
from ..errors import make_tool_error
from ..tracing import trace
from ..types import CacheAction, ModelPreset, ThinkingLevel

infra_server = FastMCP("infra")


@infra_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
@trace(name="infra_cache", span_type="TOOL")
async def infra_cache(
    action: CacheAction = "stats",
    content_id: Annotated[str | None, Field(description="Scope clear to a specific content ID")] = None,
) -> dict:
    """Manage the analysis cache — stats, list, clear, or inspect context cache state.

    Args:
        action: Cache operation — "stats", "list", "clear", or "context".
        content_id: When action is "clear", limit deletion to this content ID.

    Returns:
        Dict with operation-specific results (file_count, entries, removed count,
        or context cache diagnostics).
    """
    if action == "stats":
        return cache_mod.stats()
    if action == "list":
        return {"entries": cache_mod.list_entries()}
    if action == "clear":
        removed = cache_mod.clear(content_id)
        return {"removed": removed}
    if action == "context":
        from .. import context_cache
        return context_cache.diagnostics()
    return {"error": f"Unknown action: {action}", "valid_actions": ["stats", "list", "clear", "context"]}


@infra_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
@trace(name="infra_configure", span_type="TOOL")
async def infra_configure(
    preset: Annotated[ModelPreset | None, Field(
        description='Named model preset: "best" (3.1 Pro), "stable" (2.5 Pro), or "budget" (2.5 Flash)',
    )] = None,
    model: Annotated[str | None, Field(description="Gemini model ID override (takes precedence over preset)")] = None,
    thinking_level: ThinkingLevel | None = None,
    temperature: Annotated[float | None, Field(ge=0.0, le=2.0, description="Sampling temperature")] = None,
) -> dict:
    """Reconfigure the server at runtime — preset, model, thinking level, or temperature.

    Changes take effect immediately for all subsequent tool calls.

    Args:
        preset: Named model preset — resolves to a default_model + flash_model pair.
        model: Gemini model ID (takes precedence over preset's default_model).
        thinking_level: Thinking depth — "minimal", "low", "medium", or "high".
        temperature: Sampling temperature (0.0–2.0).

    Returns:
        Dict with current_config, active_preset, and available_presets.
    """
    try:
        overrides: dict[str, object] = {}

        if preset is not None:
            if preset not in MODEL_PRESETS:
                valid = ", ".join(sorted(MODEL_PRESETS))
                raise ValueError(f"Unknown preset '{preset}'. Available: {valid}")
            p = MODEL_PRESETS[preset]
            overrides["default_model"] = p["default_model"]
            overrides["flash_model"] = p["flash_model"]

        # Explicit model overrides preset's default_model
        if model is not None:
            overrides["default_model"] = model
        if thinking_level is not None:
            overrides["default_thinking_level"] = thinking_level
        if temperature is not None:
            overrides["default_temperature"] = temperature

        cfg = update_config(**overrides)

        # Detect which preset (if any) matches current config
        active = None
        for name, p in MODEL_PRESETS.items():
            if cfg.default_model == p["default_model"] and cfg.flash_model == p["flash_model"]:
                active = name
                break

        return {
            "current_config": cfg.model_dump(exclude={"gemini_api_key"}),
            "active_preset": active,
            "available_presets": {k: v["label"] for k, v in MODEL_PRESETS.items()},
        }
    except Exception as exc:
        return make_tool_error(exc)
