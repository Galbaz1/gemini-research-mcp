# Roadmap

Planned features for video-research-mcp. Each item links to a detailed design doc and a GitHub issue where you can track progress or contribute.

Want to pick something up? Comment on the issue. Design docs in [`docs/plans/`](docs/plans/) contain full implementation plans with file layouts, test strategies, and checklists.

## 1. Deep Research Agent

Expose Google's Gemini Deep Research Agent — an autonomous agent that plans, searches the real web (80-160 queries), reads sources, and writes cited reports. Runs 2-20 minutes per task, producing analyst-grade output with web-grounded citations. Complements the existing `research_deep` tool, which is faster but limited to Gemini's training data.

- 3 new tools: `research_agent_start`, `research_agent_poll`, `research_agent_followup`
- Start/poll pattern (like video sessions) — non-blocking for the calling agent
- Follow-up questions chain to the original research context
- All state managed server-side by Google's Interactions API — no local session store needed
- Auto-stores reports to Weaviate `ResearchFindings` collection

Design doc: [docs/plans/DEEP_RESEARCH_AGENT_PLAN.md](docs/plans/DEEP_RESEARCH_AGENT_PLAN.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/1)

## 2. Document Research

A multi-phase pipeline for deep research grounded in actual source documents. Accepts PDFs and URLs, runs four phases (ingest, extract, cross-reference, synthesize), and produces evidence-tiered findings with page-level citations. Bridges the gap between `content_analyze` (single-pass) and `research_deep` (no document input).

- 1 new tool: `research_document`
- Four-phase pipeline: Document Ingestion → Evidence Extraction → Cross-Reference → Synthesis
- Native PDF vision for charts, tables, and diagrams
- Evidence tiers with document + page citations (e.g., "p.12, Table 3")
- Cross-reference analysis surfaces agreements, contradictions, and evidence chains across documents
- Scope levels (quick/moderate/deep/comprehensive) control phase depth

Design doc: [docs/plans/DOCUMENT_RESEARCH.md](docs/plans/DOCUMENT_RESEARCH.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/2)

## 3. MLflow Tracing

Optional observability for every Gemini call. `mlflow.gemini.autolog()` patches the SDK automatically — no manual instrumentation needed for LLM spans. `@mlflow.trace` decorators on tool functions add the business-logic layer. Zero overhead when not installed.

- Optional `[tracing]` install extra using the lightweight `mlflow-tracing` package (1.5 MB)
- Three-layer trace trees: TOOL → retry → CHAT_MODEL
- Full input/output/token visibility per span
- No-op fallback when `mlflow-tracing` is not installed — zero import errors, zero performance impact
- Optional MLflow MCP server companion lets Claude Code query traces, diagnose failures, and log quality feedback
- Explicit opt-out via `GEMINI_TRACING_ENABLED=false`

Design doc: [docs/plans/MLFLOW_TRACING.md](docs/plans/MLFLOW_TRACING.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/3)

## 4. Writing Style Skill

A passive skill that bakes humanizer rules into the `/gr:*` command pipeline so every `analysis.md` reads like a competent researcher's notes, not a press release. Text generation happens client-side (Claude formatting Gemini's JSON into prose), so the rules belong in a skill that commands and agents reference at write-time.

- 1 new skill: `writing-style` (~60 lines), adapted from the humanizer's 24 patterns
- 11 AI writing patterns filtered for research/analysis context (inflated significance, promotional language, AI vocabulary, bold-colon lists, etc.)
- Applied to all 4 commands and 2 agents that write `analysis.md` prose
- No effect on MCP tool output (structured JSON) or visualizer HTML

Design doc: [docs/plans/WRITING_STYLE_SKILL_PLAN.md](docs/plans/WRITING_STYLE_SKILL_PLAN.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/4)

## 5. Video Explainer MCP

A companion MCP server wrapping [video_explainer](https://github.com/prajwal-y/video_explainer) to create explainer videos from research output. gemini-research-mcp handles extraction; this server handles synthesis. Pure CLI wrapping — no Python module imports, no dependency conflicts.

- 15 new tools across 4 sub-servers (project, pipeline, quality, audio)
- `explainer_inject` bridges research output into the video pipeline
- Full pipeline: script → narration → scenes → voiceover → storyboard → render
- Background render pattern (start/poll) for long-running 1080p+ encodes
- Distributed via the existing npm installer under `/ve:` namespace (3 commands, 1 skill, 2 agents)

Design doc: [docs/plans/VIDEO_EXPLAINER_MCP_PLAN.md](docs/plans/VIDEO_EXPLAINER_MCP_PLAN.md) | [GitHub issue](https://github.com/Galbaz1/video-research-mcp/issues/5)
