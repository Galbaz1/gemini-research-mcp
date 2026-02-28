# AGENTS.md

## Scope

Codex project instructions equivalent to this repo's Claude setup.

- Root guidance lives here.
- Source-code specific guidance lives in `src/AGENTS.md`.
- Test-specific guidance lives in `tests/AGENTS.md`.

This layout mirrors `.claude/rules/*.md` path scoping using Codex's directory-based AGENTS discovery.

## What This Is

An MCP server (stdio transport, FastMCP) exposing tools for video analysis, deep research, content extraction, web search, and context caching. Powered by Gemini (`google-genai`) and YouTube Data API v3. Python >= 3.11.

## Commands

```bash
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"
uv run pytest tests/ -v
uv run pytest tests/ -k "video_analyze" -v
uv run ruff check src/ tests/
GEMINI_API_KEY=... uv run video-research-mcp
scripts/detect_review_scope.py --json
```

## Code Review Trigger Protocol

Use `scripts/detect_review_scope.py --json` before review/audit/check requests and after major git-state transitions.

Priority when multiple states apply:
1. `uncommitted`
2. `pr`
3. `commits`

Do not mix review scopes in one pass unless explicitly requested.

## Architecture

`server.py` mounts sub-servers onto `FastMCP("video-research")`:

- `tools/video.py`: video analysis/session/batch tools
- `tools/youtube.py`: metadata/comments/playlist tools
- `tools/research.py`: deep research/planning/evidence tools
- `tools/content.py`: content analyze/extract tools
- `tools/search.py`: web search tool
- `tools/infra.py`: infra/cache/config tools
- `tools/knowledge/`: knowledge tools

Supporting modules include `video_cache.py` and `video_batch.py`.

Core project patterns:
- Instruction-driven tools (`instruction` + optional `output_schema`)
- Structured output via `GeminiClient.generate_structured(...)`
- Tools return error dicts (`make_tool_error()`), no exception escape
- Write-through Weaviate storage when configured (non-fatal)
- Context caching with prewarm + session reuse

## Conventions

### New Tools

Every tool must have:
1. `ToolAnnotations` on the decorator
2. `Annotated[...]` params with `Field(...)`
3. Google-style docstring
4. Structured output via `GeminiClient.generate_structured(...)`

Shared types belong in `types.py`.

### Docstrings

Google-style docstrings are required on modules, public classes/functions/methods, and non-obvious private helpers. Keep docstrings concise and factual.

### File Size

Aim for ~300 lines of executable production code per file (excluding docstrings/comments/blanks). Test files may go to ~500 lines.

## Dependency Policy

Pin to the major version actually used. Do not use cross-major constraints where APIs differ.

Key constraints in this project:
- `fastmcp >=3.0.2`
- `google-genai >=1.57`
- `google-api-python-client >=2.100`
- `pydantic >=2.0`
- `weaviate-client >=4.19.2`
- `pytest >=8.0`
- `pytest-asyncio >=1.0`
- `ruff >=0.9`

When updating dependencies:
1. Update `pyproject.toml`
2. Re-resolve deps
3. Remove obsolete compatibility workarounds
4. Run full tests

## Testing Summary

Tests are unit-level with mocked Gemini. No tests should hit real APIs.

Primary fixtures and patterns are documented in `tests/conftest.py` and `docs/tutorials/WRITING_TESTS.md`.

## Plugin Installer Context

Two-package architecture:
- npm package copies commands/skills/agents to `~/.claude/`
- PyPI package runs MCP server via `uvx`

See `docs/PLUGIN_DISTRIBUTION.md` for details.

## Environment Variables

Canonical source: `config.py:ServerConfig`.

Main variables:
- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (default `gemini-3.1-pro-preview`)
- `GEMINI_FLASH_MODEL` (default `gemini-3-flash-preview`)
- `WEAVIATE_URL` (empty disables knowledge store)
- `WEAVIATE_API_KEY`
- `GEMINI_SESSION_DB` (empty means in-memory sessions)

## Key Docs

- `docs/ARCHITECTURE.md`
- `docs/DIAGRAMS.md`
- `docs/tutorials/GETTING_STARTED.md`
- `docs/tutorials/ADDING_A_TOOL.md`
- `docs/tutorials/WRITING_TESTS.md`
- `docs/tutorials/KNOWLEDGE_STORE.md`
- `docs/CODE_REVIEW_AUTOMATION.md`
- `docs/PLUGIN_DISTRIBUTION.md`
- `docs/PUBLISHING.md`
- `docs/RELEASE_CHECKLIST.md`

