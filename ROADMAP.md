# Roadmap

Planned and completed features for video-research-mcp. Each item links to a design doc and GitHub issue.

Want to pick something up? Comment on the issue. Design docs in [`docs/plans/`](docs/plans/) contain implementation plans with file layouts, test strategies, and checklists.

---

## Completed

### ~~2. Document Research~~ ✓

Multi-phase pipeline for deep research grounded in actual source documents. Accepts PDFs and URLs, runs evidence-tiered extraction with page-level citations.

- `research_document` tool + `/gr:research-doc` command
- `research_document_file.py` handles File API upload and URL download
- Evidence tiers with document + page citations

Design doc: [docs/plans/DOCUMENT_RESEARCH.md](docs/plans/DOCUMENT_RESEARCH.md) | [GitHub issue (closed)](https://github.com/Galbaz1/video-research-mcp/issues/2)

### ~~3. MLflow Tracing~~ ✓

Optional observability for every Gemini call. `@trace` decorators on all 24 tools. Zero overhead when not installed.

- `tracing.py` module with guarded mlflow import
- `[tracing]` install extra using `mlflow-tracing` package
- Three-layer trace trees: TOOL → retry → CHAT_MODEL
- `/gr:traces` command + `mlflow-traces` skill
- Opt-out via `GEMINI_TRACING_ENABLED=false`

Design doc: [docs/plans/MLFLOW_TRACING.md](docs/plans/MLFLOW_TRACING.md) | [GitHub issue (closed)](https://github.com/Galbaz1/video-research-mcp/issues/3)

### ~~5. Video Explainer MCP~~ ✓

Companion MCP server wrapping video_explainer to create explainer videos from research output. 15 tools across 4 sub-servers.

- `packages/video-explainer-mcp/` — fully independent package
- Pipeline: project → scenes → render → audio → quality
- `/ve:*` namespace (3 commands, 1 skill, 2 agents)
- Background render pattern (start/poll) for long encodes

Design doc: [docs/plans/VIDEO_EXPLAINER_MCP_PLAN.md](docs/plans/VIDEO_EXPLAINER_MCP_PLAN.md) | [GitHub issue (closed)](https://github.com/Galbaz1/video-research-mcp/issues/5)

### Video Agent MCP ✓

Parallel scene generation via Claude Agent SDK. Replaces sequential LLM calls (~21 min for 7 scenes) with bounded concurrent execution (~3-5 min).

- `packages/video-agent-mcp/` — 2 tools: `agent_generate_scenes`, `agent_generate_single_scene`
- Bounded concurrency via `asyncio.Semaphore`
- Partial failure handling (N/7 scenes succeed → write those, report errors)
- CLAUDECODE env guard prevents recursive agent loops

### Knowledge Store Reranker + Flash Summarization ✓

Cohere reranking and Gemini Flash post-processing for knowledge search results.

- Overfetch pattern (3x limit) → Cohere rerank → sort by rerank_score
- Flash summarization: one-line relevance summaries, property trimming
- Auto-enables when `COHERE_API_KEY` is set
- `rerank_score` and `summary` fields on `KnowledgeHit`

### Media Asset Pipeline ✓

Local file path propagation through video/content pipelines for offline access.

- `local_media_path`, `screenshot_dir` fields in Weaviate schema
- `/gr:recall` shows local availability and offers chat shortcuts
- Write-through stores local paths alongside analysis results

---

## In Progress

### Contract Hardening (PR #19)

Video output contract enforcement with quality gates and artifact rendering. Cherry-picked from closed PR #6 — only the unique, self-contained modules.

- `contract/` package: pipeline orchestration, quality gates, artifact rendering with i18n (en/nl/es)
- `validation.py`: semantic validation for timestamps, key points, concept edges
- `schema_guard.py`: JSON schema complexity limiter
- `generate_json_validated()`: dual-path validation (Pydantic TypeAdapter / jsonschema)
- 60 tests, all passing

Design doc: [docs/plans/VIDEO_OUTPUT_CONTRACT_HARDENING.md](docs/plans/VIDEO_OUTPUT_CONTRACT_HARDENING.md) | [PR #19](https://github.com/Galbaz1/video-research-mcp/pull/19)

---

## Planned

### 1. Deep Research Agent

Expose Google's Gemini Deep Research Agent — an autonomous agent that plans, searches the real web (80-160 queries), reads sources, and writes cited reports. Runs 2-20 minutes per task.

- 3 new tools: `research_agent_start`, `research_agent_poll`, `research_agent_followup`
- Start/poll pattern — non-blocking for the calling agent
- All state managed server-side by Google's Interactions API
- Auto-stores reports to Weaviate `ResearchFindings` collection

Design doc: [docs/plans/DEEP_RESEARCH_AGENT_PLAN.md](docs/plans/DEEP_RESEARCH_AGENT_PLAN.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/1)

### 4. Writing Style Skill

A passive skill that bakes humanizer rules into the `/gr:*` command pipeline so every `analysis.md` reads like a researcher's notes, not a press release.

- 1 new skill: `writing-style` (~60 lines), adapted from the humanizer's 24 patterns
- 11 AI writing patterns filtered for research/analysis context
- Applied to all commands and agents that write `analysis.md` prose
- No effect on MCP tool output (structured JSON) or visualizer HTML

Design doc: [docs/plans/WRITING_STYLE_SKILL_PLAN.md](docs/plans/WRITING_STYLE_SKILL_PLAN.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/4)

### 6. Knowledge Conflict Detection

Detect contradictory, outdated, or inconsistent information across the knowledge store at recall time.

- 1 new tool: `knowledge_conflicts`
- Gemini-powered conflict analysis on recall results
- Four conflict types with severity levels and resolution hints
- Configurable sensitivity: strict, balanced, lenient
- `/gr:recall conflicts "topic"` command integration

Design doc: [docs/plans/KNOWLEDGE_CONFLICT_DETECTION.md](docs/plans/KNOWLEDGE_CONFLICT_DETECTION.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/9)
