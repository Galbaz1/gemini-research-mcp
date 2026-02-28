# BUG: Dict/List parameters fail Pydantic validation via MCP transport

**Reported**: 2026-02-28
**Severity**: HIGH (knowledge_ingest completely unusable, knowledge_search collections filter broken)
**Reproducible**: Yes — 100% on every call with dict or list params

## Summary

MCP tool parameters with complex types (`dict`, `list`) are serialized as JSON strings by the transport layer before reaching the Python function. Pydantic validates the input type and rejects them because it expects native Python types.

## Affected Tools

| Tool | Parameter | Type | Status |
|------|-----------|------|--------|
| `knowledge_ingest` | `properties` | `dict` | **Completely broken** — cannot ingest any data |
| `knowledge_search` | `collections` | `list[str]` | **Filter broken** — search works but can't filter by collection |
| Potentially others | Any `dict`/`list` param | — | Needs audit |

## Reproduction

```python
# knowledge_ingest — FAILS
knowledge_ingest(
    collection="VideoAnalyses",
    properties={"title": "Test", "summary": "Test", "source_tool": "manual"}
)
# Error: 1 validation error for call[knowledge_ingest]
# properties
#   Input should be a valid dictionary [type=dict_type,
#   input_value='{"title": "Test", "summary": "Test", "source_tool": "manual"}',
#   input_type=str]

# knowledge_search with collections filter — FAILS
knowledge_search(query="test", collections=["VideoAnalyses"])
# Error: 1 validation error for call[knowledge_search]
# collections
#   Input should be a valid list [type=list_type,
#   input_value='["VideoAnalyses"]', input_type=str]
```

## Root Cause

The MCP JSON-RPC transport serializes all parameters to JSON. When the parameters reach the Python function, complex types (`dict`, `list`) arrive as their JSON string representation (e.g., `'{"key": "value"}'`) instead of native Python objects.

Pydantic's strict type checking then rejects `str` where `dict` or `list` is expected.

## Suggested Fix

Add a Pydantic `@field_validator` or `model_validator` that deserializes JSON strings to their native types before validation:

```python
from pydantic import field_validator
import json

@field_validator('properties', mode='before')
@classmethod
def parse_properties(cls, v):
    if isinstance(v, str):
        return json.loads(v)
    return v
```

Or use a FastMCP middleware/hook that pre-processes all incoming parameters.

Alternative: define the parameter type as `dict | str` with a validator that handles both.

## Impact

- `knowledge_ingest` is **completely unusable** via MCP — no data can be manually inserted
- `knowledge_search` `collections` filter is broken — can only search all collections
- Write-through from tools (video_analyze, etc.) still works because those call the store functions directly in Python, bypassing MCP parameter serialization
- The Phase 3 concept/relationship ingest (from `/gr:video`) likely also fails silently

## Workaround

None for end users. The tools work correctly when called from Python directly (e.g., in unit tests or from other tool functions), but not when invoked via MCP from Claude.

## Environment

- video-research-mcp: v0.2.0 (local dev)
- FastMCP: 3.0.2
- Pydantic: 2.12
- Python: 3.12
