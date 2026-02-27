# CLAUDE.md

## What This Is

An MCP server (stdio transport, FastMCP) exposing 18 tools for video analysis, deep research, content extraction, and web search. Powered by Gemini 3.1 Pro (`google-genai` SDK) and YouTube Data API v3. Built with Pydantic v2, hatchling. Python >= 3.11.

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
| youtube | `video_metadata`, `video_playlist` | `tools/youtube.py` |
| research | `research_deep`, `research_plan`, `research_assess_evidence` | `tools/research.py` |
| content | `content_analyze`, `content_extract` | `tools/content.py` |
| search | `web_search` | `tools/search.py` |
| infra | `infra_cache`, `infra_configure` | `tools/infra.py` |
| knowledge | `knowledge_search`, `knowledge_related`, `knowledge_stats`, `knowledge_ingest` | `tools/knowledge.py` |

**Key patterns:**
- **Instruction-driven tools** — tools accept free-text `instruction` + optional `output_schema` instead of fixed modes
- **Structured output** — `GeminiClient.generate_structured(contents, schema=ModelClass)` returns validated Pydantic models
- **Error handling** — tools never raise; return `make_tool_error()` dicts with `error`, `category`, `hint`, `retryable`
- **Write-through storage** — every tool auto-stores results to Weaviate when configured; store calls are non-fatal

**Key singletons:** `GeminiClient` (client.py), `get_config()` (config.py), `session_store` (sessions.py, optional SQLite via persistence.py), `cache` (cache.py), `WeaviateClient` (weaviate_client.py).

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

## Testing

228 tests, all unit-level with mocked Gemini. `asyncio_mode=auto`. No test hits the real API.

**Key fixtures** (`conftest.py`): `mock_gemini_client` (mocks `.get()`, `.generate()`, `.generate_structured()`), `clean_config` (isolates config), autouse `GEMINI_API_KEY=test-key-not-real`.

**File naming:** `test_<domain>_tools.py` for tools, `test_<module>.py` for non-tool modules.

> Full guide: `docs/tutorials/WRITING_TESTS.md`

## Plugin Installer

Claude Code plugin distributed via npm. `bin/install.js` copies commands/skills/agents to `~/.claude/`. File map in `bin/lib/copy.js`, manifest tracking in `bin/lib/manifest.js`.

```bash
npx video-research-mcp@latest              # install
npx video-research-mcp@latest --check      # dry-run
npx video-research-mcp@latest --uninstall  # remove
```

To add a command/skill/agent: create file, add to `FILE_MAP` in `bin/lib/copy.js`, run `node bin/install.js --global`.

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

All other config (thinking level, temperature, cache dir/TTL, session limits, retry params, YouTube API key) has sensible defaults — see `config.py` or `docs/ARCHITECTURE.md` §10.

## Developer Docs

| Document | Contents |
|----------|----------|
| `docs/ARCHITECTURE.md` | Full technical manual — 13 sections covering every pattern and module |
| `docs/DIAGRAMS.md` | Server hierarchy, GeminiClient flow, session lifecycle, Weaviate data flow |
| `docs/tutorials/GETTING_STARTED.md` | Install, configure, first tool call |
| `docs/tutorials/ADDING_A_TOOL.md` | Step-by-step tool creation with checklist |
| `docs/tutorials/WRITING_TESTS.md` | Fixtures, patterns, running tests |
| `docs/tutorials/KNOWLEDGE_STORE.md` | Weaviate setup, 7 collections, 4 knowledge tools |
