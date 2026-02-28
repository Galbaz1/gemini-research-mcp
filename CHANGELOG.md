# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-28

### Added

- **Knowledge store** — 7 Weaviate collections with write-through storage from every tool
- **Knowledge tools** — `knowledge_search`, `knowledge_related`, `knowledge_stats`, `knowledge_fetch`, `knowledge_ingest` for querying stored results
- **QueryAgent tools** — `knowledge_ask` and `knowledge_query` powered by `weaviate-agents` (optional dependency)
- **YouTube tools** — `video_metadata`, `video_comments`, `video_playlist` via YouTube Data API v3
- **Context caching** — automatic Gemini cache pre-warming after `video_analyze`; session reuse via `lookup_or_await()`
- **Session persistence** — optional SQLite backend for video Q&A sessions (`GEMINI_SESSION_DB`)
- **Plugin installer** — npm package that copies commands, skills, and agents to `~/.claude/` and configures MCP server
- **Diagnostics** — `/gr:doctor` command for MCP wiring, API key, and Weaviate connectivity checks
- **Retry logic** — exponential backoff with jitter for Gemini API calls
- **Batch analysis** — `video_batch_analyze` for concurrent directory-level video processing
- **PyPI metadata** — classifiers, project URLs, version alignment with npm

### Changed

- Bumped version from 0.1.0 to 0.2.0 (aligned with npm package)
- Unified tool count to 23 across all documentation

## [0.1.0] - 2026-02-01

### Added

- **Core server** — FastMCP root with 7 mounted sub-servers (stdio transport)
- **Video analysis** — `video_analyze`, `video_create_session`, `video_continue_session` for YouTube URLs and local files
- **Research tools** — `research_deep` (multi-phase with evidence tiers), `research_plan`, `research_assess_evidence`
- **Content tools** — `content_analyze`, `content_extract` with caller-provided JSON schemas
- **Search** — `web_search` via Gemini grounding with source citations
- **Infrastructure** — `infra_cache` (view/list/clear), `infra_configure` (runtime model/thinking/temperature)
- **Structured output** — `GeminiClient.generate_structured()` with Pydantic model validation
- **Thinking support** — configurable thinking levels (minimal/low/medium/high) via `ThinkingConfig`
- **Error handling** — `make_tool_error()` with category, hint, and retryable flag (tools never raise)
- **Caching** — file-based analysis cache with configurable TTL

[0.2.0]: https://github.com/Galbaz1/video-research-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Galbaz1/video-research-mcp/releases/tag/v0.1.0
