# CLAUDE.md

## What This Is

An MCP server (stdio transport, FastMCP) exposing 23 tools for video analysis, deep research, content extraction, web search, and context caching. Powered by Gemini 3.1 Pro (`google-genai` SDK) and YouTube Data API v3. Built with Pydantic v2, hatchling. Python >= 3.11.

## Commands

```bash
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"  # install
uv run pytest tests/ -v                                              # all tests
uv run pytest tests/ -k "video_analyze" -v                           # filtered
uv run ruff check src/ tests/                                        # lint
GEMINI_API_KEY=... uv run video-research-mcp                         # run server
```

## Architecture

`server.py` mounts 7 sub-servers onto a root `FastMCP("video-research")`:

| Sub-server | Tools | File |
|------------|-------|------|
| video | `video_analyze`, `video_create_session`, `video_continue_session`, `video_batch_analyze` | `tools/video.py` |
| youtube | `video_metadata`, `video_comments`, `video_playlist` | `tools/youtube.py` |
| research | `research_deep`, `research_plan`, `research_assess_evidence` | `tools/research.py` |
| content | `content_analyze`, `content_extract` | `tools/content.py` |
| search | `web_search` | `tools/search.py` |
| infra | `infra_cache`, `infra_configure` | `tools/infra.py` |
| knowledge | `knowledge_search`, `knowledge_related`, `knowledge_stats`, `knowledge_ingest`, `knowledge_fetch`, `knowledge_ask`, `knowledge_query` | `tools/knowledge/` |

Supporting modules: `video_cache.py` (context cache warming), `video_batch.py` (batch analysis orchestration).

**Key patterns:**
- **Instruction-driven tools** — tools accept free-text `instruction` + optional `output_schema` instead of fixed modes
- **Structured output** — `GeminiClient.generate_structured(contents, schema=ModelClass)` returns validated Pydantic models
- **Error handling** — tools never raise; return `make_tool_error()` dicts with `error`, `category`, `hint`, `retryable`
- **Write-through storage** — every tool auto-stores results to Weaviate when configured; store calls are non-fatal
- **Context caching** — `context_cache.py` pre-warms Gemini caches after `video_analyze`; `video_create_session` reuses them via `lookup_or_await()`

**Key singletons:** `GeminiClient` (client.py), `get_config()` (config.py), `session_store` (sessions.py, optional SQLite via persistence.py), `cache` (cache.py), `WeaviateClient` (weaviate_client.py).

**Optional dependency:** `weaviate-agents>=1.2.0` (install via `pip install video-research-mcp[agents]`) enables `knowledge_ask` and `knowledge_query` tools powered by Weaviate's QueryAgent.

> Deep dive: `docs/ARCHITECTURE.md` (13 sections) | `docs/DIAGRAMS.md` (4 Mermaid diagrams)

## Conventions

### New Tools

Every tool MUST have: (1) `ToolAnnotations` decorator, (2) `Annotated` params with `Field`, (3) Google-style docstring with Args/Returns, (4) structured output via `GeminiClient.generate_structured()`. Shared types live in `types.py`.

```python
@server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def my_tool(
    instruction: Annotated[str, Field(description="What to extract")],
    thinking_level: ThinkingLevel = "medium",
) -> dict:
    """One-line summary of what this tool does.

    Args:
        instruction: Free-text analysis instruction.

    Returns:
        Dict with structured results or error via make_tool_error().
    """
```

> Full walkthrough: `docs/tutorials/ADDING_A_TOOL.md`

### Docstrings

Google-style. Required on every module, public class, public function/method, and non-obvious private helpers. Be concise and factual — one-liner is enough when name + signature are self-explanatory. Args/Returns/Raises only when non-obvious. Pydantic models: document purpose and which tool uses them; don't duplicate `Field(description=...)`. Docstrings do NOT count toward file size limits.

### File Size

~300 lines of executable code per production file (docstrings/comments/blanks excluded). Split by concern, not by line count. Test files may go to 500. Reference: `video.py` / `video_url.py` split.

## Dependencies

### Constraint Policy

Pin to the **major version we actually use**. No cross-major constraints — a constraint like `>=2.0` that accepts both 2.x and 3.x is forbidden when the major versions have breaking API changes. Rationale: overly broad constraints hide version-specific code and create silent compatibility debt (ref: FastMCP 2.x→3.x FunctionTool wrapping incident).

**Format:** `>=MAJOR.MINOR` where MINOR is the lowest version whose API surface we actually use. Never `>=MAJOR.0` unless we've verified compatibility with the .0 release.

### Pinned Dependencies

| Package | Constraint | Installed | API Surface We Use | Rationale |
|---------|-----------|-----------|-------------------|-----------|
| `fastmcp` | `>=3.0.2` | 3.0.2 | `FastMCP`, `.mount()`, `.tool()`, `.run()`, `@asynccontextmanager` lifespan | 3.x preserves tool callability; 2.x wraps in non-callable `FunctionTool` |
| `google-genai` | `>=1.57` | 1.65.0 | `genai.Client`, `ThinkingConfig`, `cached_content`, Gemini 3.1 model strings, async `generate_content` | 1.56 added ThinkingConfig; 1.57 added Gemini 3 model support. Preview/beta SDK versions are fine for this project |
| `google-api-python-client` | `>=2.100` | 2.190.0 | YouTube Data API v3 via `build("youtube", "v3")` | Pure REST wrapper; API stable within v2. `>=2.100` is fine |
| `pydantic` | `>=2.0` | 2.12.5 | v2 only: `BaseModel`, `Field`, `model_validator`, `ConfigDict`, `model_dump()` | No v1 patterns anywhere. v3 doesn't exist yet. `>=2.0` is correct |
| `weaviate-client` | `>=4.19.2` | 4.20.1 | v4 collections API: `client.collections.get()`, `weaviate.classes.*`, `AsyncQueryAgent` | v4 is a complete rewrite from v3. Constraint correctly pins v4 |
| `pytest` | `>=8.0` | 9.0.2 | Standard API | pytest 9.x is backwards compatible. `>=8.0` is fine |
| `pytest-asyncio` | `>=1.0` | 1.3.0 | `asyncio_mode = "auto"` (pyproject.toml) | Major rewrite in 1.0 (from 0.x). `asyncio_mode=auto` is 0.18+ but 1.x API is cleaner. Update constraint to `>=1.0` |
| `ruff` | `>=0.9` | 0.15.4 | CLI linter/formatter | Pre-1.0; minor versions may change rules. Acceptable |

### Known Defensive Patterns (Legitimate)

These `getattr` patterns protect against **SDK response shape variation**, not version incompatibility — do NOT remove:

- `getattr(p, "thought", False)` — Gemini thinking mode parts; `thought` attr only present when thinking is enabled
- `getattr(cand, "grounding_metadata", None)` — search grounding; only present on grounded responses
- `getattr(response, "final_answer", "")` in knowledge/agent.py — weaviate-agents response shape varies by query type
- `try: from googleapiclient.errors import HttpError` in tools/youtube.py — guards error formatting when google-api-python-client isn't importable

### Updating Dependencies

When bumping a dependency:
1. Update constraint in `pyproject.toml`
2. Run `uv pip install -e ".[dev]"` to resolve
3. Search for compatibility workarounds that may now be removable (`grep -r "2\.x\|v1\|compat\|shim\|workaround"`)
4. Run full test suite: `uv run pytest tests/ -v`

## Agent Teams

Default model for all subagent teams: **Claude Opus 4.6** (`model: "opus"`). This is a hard project requirement — do not use a lighter model for team agents unless the user explicitly requests it.

Agent configuration: `.claude/rules/` contains project-specific conventions that agents inherit automatically via path-filtered frontmatter.

## Testing

417 tests, all unit-level with mocked Gemini. `asyncio_mode=auto`. No test hits the real API.

**Key fixtures** (`conftest.py`): `mock_gemini_client` (mocks `.get()`, `.generate()`, `.generate_structured()`), `clean_config` (isolates config), `_unwrap_fastmcp_tools` (session-scoped, ensures tool callability), autouse `GEMINI_API_KEY=test-key-not-real`.

**File naming:** `test_<domain>_tools.py` for tools, `test_<module>.py` for non-tool modules.

> Full guide: `docs/tutorials/WRITING_TESTS.md` | Project-specific patterns: `.claude/rules/testing.md`

## Plugin Installer

Two-package architecture: npm (installer) copies commands/skills/agents to `~/.claude/`, PyPI (server) runs via `uvx`. Same package name, different registries.

```bash
npx video-research-mcp@latest              # install plugin (copies 17 markdown files + .mcp.json)
npx video-research-mcp@latest --check      # dry-run
npx video-research-mcp@latest --uninstall  # remove
```

To add a command/skill/agent: create file, add to `FILE_MAP` in `bin/lib/copy.js`, run `node bin/install.js --global`.

> Deep dive: `docs/PLUGIN_DISTRIBUTION.md` (FILE_MAP, manifest tracking, discovery mechanism, complete inventory)

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

The server auto-loads `~/.config/video-research-mcp/.env` at startup. Process env vars always take precedence over the config file. This ensures keys are available in any workspace, even without direnv.

All other config (thinking level, temperature, cache dir/TTL, session limits, retry params, YouTube API key) has sensible defaults — see `config.py` or `docs/ARCHITECTURE.md` §10.

## Developer Docs

| Document | Contents |
|----------|----------|
| `docs/ARCHITECTURE.md` | Full technical manual — 13 sections covering every pattern and module |
| `docs/DIAGRAMS.md` | Server hierarchy, GeminiClient flow, session lifecycle, Weaviate data flow |
| `docs/tutorials/GETTING_STARTED.md` | Install, configure, first tool call |
| `docs/tutorials/ADDING_A_TOOL.md` | Step-by-step tool creation with checklist |
| `docs/tutorials/WRITING_TESTS.md` | Fixtures, patterns, running tests |
| `docs/tutorials/KNOWLEDGE_STORE.md` | Weaviate setup, 7 collections, 8 knowledge tools |
| `docs/PLUGIN_DISTRIBUTION.md` | Two-package architecture, FILE_MAP, discovery, full inventory |
| `docs/WEAVIATE_PLUGIN_RECOMMENDATION.md` | Gap analysis and roadmap for knowledge store plugin assets |
| `docs/PUBLISHING.md` | Dual-registry publishing guide with version sync policy |
| `docs/RELEASE_CHECKLIST.md` | Copy-paste checklist for each release |
| `CHANGELOG.md` | Release history in Keep a Changelog format |
| `docs/plans/` | Design docs for planned features — linked from `ROADMAP.md` and GitHub issues |
