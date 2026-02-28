# CLAUDE.md

## Memory Source Guard

Do not import `AGENTS.md` from this file or any `.claude/rules/*.md` file. `AGENTS.md` is Codex-specific.

## What This Is

An MCP server (stdio transport, FastMCP) exposing 25 tools for video analysis, deep research, content extraction, web search, and context caching. Powered by Gemini 3.1 Pro (`google-genai` SDK) and YouTube Data API v3. Built with Pydantic v2, hatchling. Python >= 3.11.

## Commands

```bash
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"  # install
uv run pytest tests/ -v                                              # all tests
uv run pytest tests/ -k "video_analyze" -v                           # filtered
uv run ruff check src/ tests/                                        # lint
GEMINI_API_KEY=... uv run video-research-mcp                         # run server
scripts/detect_review_scope.py --json                                # auto-select review scope
```

## Architecture

`server.py` mounts 7 sub-servers onto a root `FastMCP("video-research")`:

| Sub-server | Tools | File |
|------------|-------|------|
| video | `video_analyze`, `video_create_session`, `video_continue_session`, `video_batch_analyze` | `tools/video.py` |
| youtube | `video_metadata`, `video_comments`, `video_playlist` | `tools/youtube.py` |
| research | `research_deep`, `research_plan`, `research_assess_evidence`, `research_document` | `tools/research.py` |
| content | `content_analyze`, `content_extract`, `content_batch_analyze` | `tools/content.py` |
| search | `web_search` | `tools/search.py` |
| infra | `infra_cache`, `infra_configure` | `tools/infra.py` |
| knowledge | `knowledge_search`, `knowledge_related`, `knowledge_stats`, `knowledge_ingest`, `knowledge_fetch`, `knowledge_ask`, `knowledge_query` | `tools/knowledge/` |

**Key patterns:**
- **Instruction-driven tools** — free-text `instruction` + optional `output_schema` instead of fixed modes
- **Structured output** — `GeminiClient.generate_structured(contents, schema=ModelClass)` returns validated Pydantic models
- **Error handling** — tools never raise; return `make_tool_error()` dicts
- **Write-through storage** — auto-stores results to Weaviate when configured; non-fatal
- **Context caching** — `context_cache.py` pre-warms Gemini caches; sessions reuse via `ensure_session_cache()`
- **Deferred tool registration** — `_ensure_*_tool()` functions called from `server.py` before mounting, to avoid circular imports when batch/document tool modules import from their parent

**Key singletons:** `GeminiClient` (client.py), `get_config()` (config.py), `session_store` (sessions.py), `cache` (cache.py), `WeaviateClient` (weaviate_client.py).

**Optional dependency:** `weaviate-agents>=1.2.0` enables `knowledge_ask` and `knowledge_query` tools.

> Deep dive: `docs/ARCHITECTURE.md` | `docs/DIAGRAMS.md`

## Conventions

### New Tools

Every tool MUST have: (1) `ToolAnnotations` decorator, (2) `Annotated` params with `Field`, (3) Google-style docstring with Args/Returns, (4) structured output via `GeminiClient.generate_structured()`. Shared types live in `types.py`.

```python
@server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def my_tool(
    instruction: Annotated[str, Field(description="What to extract")],
    thinking_level: ThinkingLevel = "medium",
) -> dict:
    """One-line summary.

    Args:
        instruction: Free-text analysis instruction.

    Returns:
        Dict with structured results or error via make_tool_error().
    """
```

> Full walkthrough: `docs/tutorials/ADDING_A_TOOL.md`

Code style (docstrings, file size limits, module structure): see `.claude/rules/python.md`.

## Dependencies

Pin to the **major version we actually use**. No cross-major constraints when APIs differ. Format: `>=MAJOR.MINOR` where MINOR is the lowest version whose API we call.

| Package | Constraint | Rationale |
|---------|-----------|-----------|
| `fastmcp` | `>=3.0.2` | 3.x preserves tool callability; 2.x wraps in non-callable `FunctionTool` |
| `google-genai` | `>=1.57` | 1.57 added Gemini 3 model support. Preview/beta OK |
| `google-api-python-client` | `>=2.100` | YouTube Data API v3. Pure REST wrapper, stable within v2 |
| `httpx` | `>=0.27` | Async document downloads in `research_document_file.py` |
| `pydantic` | `>=2.0` | v2 only: `BaseModel`, `Field`, `model_dump()` |
| `weaviate-client` | `>=4.19.2` | v4 collections API (complete rewrite from v3) |

> Known defensive `getattr` patterns (SDK response shape variation): see `docs/ARCHITECTURE.md` §4.

## Agent Teams

Default model for all subagent teams: **Claude Opus 4.6** (`model: "opus"`). Hard project requirement — do not use a lighter model unless the user explicitly requests it.

## Testing

520 tests, all unit-level with mocked Gemini. `asyncio_mode=auto`. No test hits the real API.

**Key fixtures** (`conftest.py`): `mock_gemini_client`, `clean_config`, `mock_weaviate_client`, `_unwrap_fastmcp_tools` (session-scoped), autouse `GEMINI_API_KEY=test-key-not-real`.

**File naming:** `test_<domain>_tools.py` for tools, `test_<module>.py` for non-tool modules.

> Patterns: `.claude/rules/testing.md` | Full guide: `docs/tutorials/WRITING_TESTS.md`

## Plugin Installer

Two-package architecture: npm (installer) copies commands/skills/agents to `~/.claude/`, PyPI (server) runs via `uvx`. Same package name, different registries.

```bash
npx video-research-mcp@latest              # install plugin
npx video-research-mcp@latest --check      # dry-run
npx video-research-mcp@latest --uninstall  # remove
```

To add a command/skill/agent: create file, add to `FILE_MAP` in `bin/lib/copy.js`, run `node bin/install.js --global`.

> Deep dive: `docs/PLUGIN_DISTRIBUTION.md`

## Env Vars

Canonical source: `config.py:ServerConfig`. Key variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | (required) | Also used as YouTube fallback |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | |
| `WEAVIATE_URL` | `""` | Empty = knowledge store disabled |
| `WEAVIATE_API_KEY` | `""` | Required for Weaviate Cloud |
| `GEMINI_SESSION_DB` | `""` | Empty = in-memory only |

Auto-loads `~/.config/video-research-mcp/.env` at startup. Process env vars always take precedence.

> All config options: `config.py` or `docs/ARCHITECTURE.md` §10.

## Developer Docs

All docs live in `docs/`. Key entry points: `ARCHITECTURE.md` (full technical manual), `tutorials/` (getting started, adding tools, writing tests, knowledge store), `PLUGIN_DISTRIBUTION.md`, `plans/` (design docs for planned features).
