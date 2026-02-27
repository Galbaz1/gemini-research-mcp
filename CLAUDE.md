# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An MCP server (stdio transport, FastMCP 3.0.2) exposing Gemini 3.1 Pro as 11 instruction-driven tools for video analysis, deep research, content extraction, and web search. Built with `google-genai` SDK, Pydantic v2, hatchling build backend. Requires Python >= 3.11.

## Commands

```bash
# Install for development
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"

# Run all tests (asyncio_mode=auto, no real API calls)
uv run pytest tests/ -v

# Run a single test file or test
uv run pytest tests/test_video_tools.py -v
uv run pytest tests/test_video_tools.py::test_name -v

# Run tests matching a keyword
uv run pytest tests/ -k "video_analyze" -v

# Lint (line-length=100, target py311)
uv run ruff check src/ tests/

# Run the MCP server locally
GEMINI_API_KEY=... uv run gemini-research-mcp
```

## Architecture

**Composite FastMCP server** — `server.py` creates a root `FastMCP("gemini-research")` and mounts 5 sub-servers:

```
server.py (root, lifespan hook for cleanup)
├── types.py                → shared Literal types + Annotated aliases
├── tools/video.py          → video_server    (3 tools)
├── tools/video_url.py      → URL validation helpers
├── tools/research.py       → research_server (3 tools)
├── tools/content.py        → content_server  (2 tools)
├── tools/search.py         → search_server   (1 tool)
└── tools/infra.py          → infra_server    (2 tools)
```

**Instruction-driven tools:** Tools accept an `instruction` parameter (free text) instead of fixed modes. The LLM client writes the instruction, Gemini returns structured JSON via `response_json_schema`. Tools also accept an optional `output_schema` dict for caller-defined response shapes.

**Structured output pattern:** Most tools use `GeminiClient.generate_structured(contents, schema=ModelClass)` which calls `generate()` with the model's JSON schema, then validates via `schema.model_validate_json(raw)`. This replaces all regex/line-scanning parsers from the previous architecture.

**Key singletons:**
- `GeminiClient` (`client.py`) — process-wide client pool keyed by API key. Two entry points: `generate()` returns raw text, `generate_structured()` returns a validated Pydantic model.
- `get_config()` (`config.py`) — lazy-init `ServerConfig` from env vars with Pydantic `field_validator`. Mutable at runtime via `update_config()` / the `infra_configure` tool.
- `session_store` (`sessions.py`) — in-memory `SessionStore` for multi-turn video sessions with TTL eviction and bounded history trimming.
- `cache` module (`cache.py`) — file-based JSON cache keyed by `{content_id}_{tool}_{instruction_hash}_{model_hash}`. The instruction hash differentiates results for the same content analysed with different instructions.

**Input validation:** Tool params use `Literal` types (`ThinkingLevel`, `Scope`, `CacheAction`) from `types.py` for schema-level validation. `Annotated[type, Field(...)]` adds constraints and descriptions. YouTube URLs are validated against actual youtube.com/youtu.be hosts (rejects spoofed domains).

**Tool annotations:** All 11 tools carry `ToolAnnotations` (from `mcp.types`) declaring `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint`.

**Error handling:** Tools catch exceptions and return `make_tool_error()` dicts (from `errors.py`) with `error`, `category`, `hint`, and `retryable` fields. Convention is to never raise — always return a dict.

**URL-context grounding:** `content_analyze` (URL path) uses `UrlContext()` tool wiring with a fallback to two-step (fetch unstructured, then reshape with structured output) if `response_json_schema` and `UrlContext` don't compose.

**Prompt templates** live in `prompts/` — `prompts/research.py` has research phase prompts, `prompts/content.py` has the `STRUCTURED_EXTRACT` template. Video and content tools use instruction params directly.

**Pydantic models** live in `models/` — one file per domain. These serve as both output schemas for Gemini structured output and response types for tool returns.

## Tool Surface (11 tools)

| Tool | Server | Input | Output Schema |
|------|--------|-------|---------------|
| `video_analyze` | video | url + instruction + optional schema | `VideoResult` or custom |
| `video_create_session` | video | url + description | `SessionInfo` |
| `video_continue_session` | video | session_id + prompt | `SessionResponse` |
| `research_deep` | research | topic + scope | `ResearchReport` |
| `research_plan` | research | topic + scope + agents | `ResearchPlan` |
| `research_assess_evidence` | research | claim + sources | `EvidenceAssessment` |
| `content_analyze` | content | instruction + file/url/text + optional schema | `ContentResult` or custom |
| `content_extract` | content | content + schema | caller-provided schema |
| `web_search` | search | query + num_results | grounded sources dict |
| `infra_cache` | infra | action + content_id | cache stats/entries/removed |
| `infra_configure` | infra | model/thinking/temp overrides | current config |

### Instruction Examples

```python
# Video: flexible analysis
video_analyze(url="...", instruction="List all recipes and ingredients shown")
video_analyze(url="...", instruction="Extract every CLI command demonstrated")
video_analyze(url="...", instruction="Transcribe this video with timestamps")

# Content: absorbs old summarize + analyze + web_analyze
content_analyze(url="https://arxiv.org/...", instruction="Extract the methodology section")
content_analyze(text="...", instruction="Summarize in 2 sentences")
content_analyze(file_path="paper.pdf", instruction="List all citations")

# Custom output schemas
video_analyze(url="...", instruction="List recipes", output_schema={"type": "object", "properties": {"recipes": {"type": "array"}}})
```

## File Size Guidelines

Aim for **~300 lines of code per production file** (`src/`). This is a guideline, not a hard rule. Docstrings, comments, and blank lines do NOT count; only executable code lines matter.

When a file grows past 300 code lines, treat it as a signal to look for natural seams to split on (see `video.py` / `video_url.py` split as reference). Always split by concern, never by line number. Test files may go up to 500 lines.

## Tool Conventions

Every tool MUST have:

1. **`ToolAnnotations`** in the decorator:
   ```python
   from mcp.types import ToolAnnotations
   @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
   ```
2. **`Annotated` params** with `Field` constraints for schema-level validation:
   ```python
   from typing import Annotated
   from pydantic import Field
   async def my_tool(
       instruction: Annotated[str, Field(description="...")],
       thinking_level: ThinkingLevel = "medium",
   ) -> dict:
   ```
3. **Docstring** with Args/Returns sections.
4. **Structured output** via `GeminiClient.generate_structured(schema=MyModel)` for default schemas, or `GeminiClient.generate(response_schema=custom_dict)` for caller-provided schemas.

Shared `Literal` types and `Annotated` aliases live in `types.py`.

## Testing

Tests mock `GeminiClient.get()`, `.generate()`, and `.generate_structured()` via the `mock_gemini_client` fixture in `conftest.py`. An autouse fixture sets `GEMINI_API_KEY=test-key-not-real` — no test should ever hit the real API. Use `clean_config` fixture when testing config behavior.

72 tests, all unit-level with mocked Gemini. No pytest markers. `asyncio_mode=auto` is pre-configured.

### Writing Tests for New Tools

1. **Test tool functions** using `mock_gemini_client` — set `mock_gemini_client["generate_structured"].return_value` to a Pydantic model instance, or `mock_gemini_client["generate"].return_value` to a JSON string. Call the tool, assert on the returned dict.
2. **Test models** in `tests/test_models.py` — validate defaults, roundtrip serialization.
3. **Test helpers** (URL validation, content part building) as pure function tests.
4. **File naming**: `test_<domain>_tools.py` for tool tests, `test_<module>.py` for non-tool modules.

## Env Vars

All env vars with defaults — see `config.py:ServerConfig.from_env()` for canonical source:

| Variable | Default |
|----------|---------|
| `GEMINI_API_KEY` | (required) |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` |
| `GEMINI_THINKING_LEVEL` | `high` |
| `GEMINI_TEMPERATURE` | `1.0` |
| `GEMINI_CACHE_DIR` | `~/.cache/gemini-research-mcp/` |
| `GEMINI_CACHE_TTL_DAYS` | `30` |
| `GEMINI_MAX_SESSIONS` | `50` |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `2` |
| `GEMINI_SESSION_MAX_TURNS` | `24` |
