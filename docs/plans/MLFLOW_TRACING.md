# MLflow Tracing Integration — Research & Implementation Guide

Research findings for adding optional MLflow tracing to video-research-mcp.
Verified against MLflow 3.10.0 documentation (February 2026).

## Grounding: Why MLflow Tracing?

An MCP server that wraps Gemini LLM calls is a black box to its consumers. When something goes wrong — slow responses, unexpected outputs, token budget overruns — there is no visibility into what happened inside the server. MLflow Tracing solves this by capturing per-request execution trees (traces) with spans for each LLM call, including prompts, responses, token usage, latency, and errors.

### Why MLflow over OpenTelemetry / LangSmith / custom logging?

| Criterion | MLflow Tracing | Raw OpenTelemetry | LangSmith |
|-----------|---------------|-------------------|-----------|
| Gemini SDK support | Native (`mlflow.gemini.autolog()`) | Manual instrumentation | No native Gemini support |
| Lightweight package | `mlflow-tracing` (1.5 MB wheel) | `opentelemetry-sdk` (~2 MB) | `langsmith` (~10 MB) |
| Self-hosted | Yes (local files or MLflow server) | Requires collector + backend | SaaS only |
| Async Python | Native since MLflow 3.2.0 | Native | Native |
| Open source | Apache 2.0 | Apache 2.0 | Proprietary backend |
| Production SDK | `mlflow-tracing` (95% smaller than full `mlflow`) | Core SDK | Full package required |
| OTel compatibility | First-class export to OTel backends | Native | N/A |
| MCP server | 9-tool MCP server for agent access to traces | None | None |
| Prompt registry | Built-in versioned prompt management | None | LangSmith Hub |
| GenAI evaluation | Offline batch + online LLM judges | Manual | Built-in |

MLflow wins because it already knows how to trace `google-genai` SDK calls automatically, offers a lightweight production package, can run fully self-hosted, and provides both an MCP server (for agent-driven debugging) and evaluation framework (for automated quality testing).

## Who Uses MLflow — Two Consumer Paths

This integration serves two distinct users with different needs. The implementation must address both.

### Path 1: Developer — debugging, costs, optimization

The developer installs `video-research-mcp[tracing]` and wants:

- **Full visibility into every API call** — see the exact prompt sent to Gemini, the exact response, token counts, latency per span, cost attribution
- **Organized experiments** — group traces by tool, by session, by user to identify patterns (which tools are expensive, which prompts underperform)
- **Retry transparency** — when a 429 triggers 3 retries, see each attempt's timing and the backoff delay
- **Error diagnosis** — when structured output parsing fails, see both the raw LLM response and the validation error in the same trace tree
- **Cost tracking** — token usage per span (`input_tokens`, `output_tokens`) as attributes under `mlflow.chat.tokenUsage`, aggregatable via `search_traces()`

The developer's workflow:
1. Install `[tracing]` extra
2. Run the server — traces appear in `./mlruns/` or a remote MLflow server
3. Open `mlflow ui` → browse experiment → drill into individual traces
4. See the full span tree: TOOL → CHAT_MODEL(s) → I/O
5. Compare traces to identify performance regressions
6. Run offline evaluations on collected traces (no re-running Gemini)

### Path 2: Claude Code Agent — self-improvement via trace analysis

Claude Code uses this plugin as an MCP server. When tracing is enabled, Claude Code can also use the **MLflow MCP server** (separate MCP server, 9 tools) to query traces programmatically and improve its own usage patterns:

- **Search traces** — find slow calls, failed calls, high-cost calls across experiments
- **Read trace details** — inspect specific tool calls including full prompt/response text
- **Log feedback** — attach quality scores to traces (thumbs up/down, structured ratings)
- **Log expectations** — record ground truth labels for evaluation
- **Tag traces** — add context like session ID, task type, user intent

The agent's workflow:
1. During setup, the plugin offers to install the MLflow MCP server (`mlflow[mcp]>=3.5.1`)
2. A skill teaches Claude Code how to interpret traces and what to look for
3. Claude Code can search traces to identify patterns: "which `research_deep` calls took >30s?", "what prompts produced schema validation errors?"
4. Based on findings, Claude Code can suggest prompt improvements or configuration changes
5. Claude Code can log assessments on traces to track quality over time

### Why both paths matter

Without Path 1, traces are collected but never viewed — pure overhead. Without Path 2, the developer must manually analyze traces instead of leveraging Claude Code's ability to pattern-match across hundreds of traces programmatically. Together, they create a feedback loop: traces → analysis → improvement → better traces.

## Key Findings

### 1. MLflow has native Gemini autolog support

`mlflow.gemini.autolog()` patches both the `google-genai` SDK (recommended) and legacy `google-generativeai` SDK. For this project, which uses `google-genai` (`import google.genai as genai`), autolog patches:

- `client.models.generate_content()` (sync)
- `client.aio.models.generate_content()` (async, since MLflow 3.2.0)
- Chat methods (`client.chats.create()` → `chat.send_message()`)

Every call through `GeminiClient.get().aio.models.generate_content()` is automatically traced with:

- Prompt contents (inputs) — full text visible in trace UI
- Response text (outputs) — full text visible in trace UI
- Token usage (`input_tokens`, `output_tokens`, `total_tokens`) under `mlflow.chat.tokenUsage`
- Model name, temperature, max_tokens
- Function calling (if present in response)
- Latency, exceptions

No manual instrumentation needed at the SDK level.

**Limitations:** Streaming and image/video inputs are not captured by autolog. The legacy `google-generativeai` SDK may be dropped without notice — this project already uses the recommended `google-genai` SDK.

### 2. Servers don't need MLflow runs

In MLflow 3.x, tracing is fully decoupled from runs. `mlflow.start_run()` is unnecessary for a long-running MCP server. Traces log directly to an experiment — one trace per incoming tool call, automatically opened and closed by the `@mlflow.trace` decorator.

Lifecycle:
1. Server boots → `setup_tracing()` calls `set_tracking_uri()`, `set_experiment()`, `gemini.autolog()` once
2. Request arrives → `@mlflow.trace` on tool function opens a new trace
3. Nested Gemini calls → autolog creates child `CHAT_MODEL` spans within the same trace
4. Weaviate store calls → appear as I/O spans after LLM processing
5. Request completes → trace finalized, queued for async export in background thread pool
6. Server shuts down → `shutdown_tracing()` flushes pending traces via `mlflow.flush_trace_async_logging()`

### 3. Three-layer tracing architecture

Combining autolog (SDK-level) with manual `@mlflow.trace` decorators (tool-level) gives a complete execution tree per request. The `with_retry()` wrapper around every Gemini call means retry attempts appear as sibling `CHAT_MODEL` spans:

```
video_analyze (TOOL)                                    ← @mlflow.trace decorator
├── generate_content [attempt 1] (CHAT_MODEL)           ← mlflow.gemini.autolog()
├── generate_content [attempt 2 - retry] (CHAT_MODEL)   ← autolog (if 429/503)
└── weaviate_store.store_video_analysis                  ← I/O (optional)

research_deep (AGENT)                                   ← @mlflow.trace decorator
├── generate [scope_definition] (CHAT_MODEL)            ← autolog (unstructured)
├── generate_content [evidence_collection] (CHAT_MODEL) ← autolog (structured)
├── generate_content [synthesis] (CHAT_MODEL)           ← autolog (structured)
└── weaviate_store.store_research_finding               ← I/O (optional)

knowledge_search (RETRIEVER)                            ← @mlflow.trace decorator
└── WeaviateClient.query                                ← manual span (no LLM)

web_search (TOOL)                                       ← @mlflow.trace decorator
├── generate_content [grounded] (CHAT_MODEL)            ← autolog
└── weaviate_store.store_web_search                     ← I/O (optional)
```

**Why three layers, not two:** Every `GeminiClient.generate()` call wraps the underlying `client.aio.models.generate_content()` in `with_retry()`. Autolog patches the inner method (not the retry lambda), so each retry attempt gets its own `CHAT_MODEL` span. On a 429 with 2 retries, you see 3 sibling `CHAT_MODEL` spans — making retry behavior visible in traces.

### 4. Lightweight production package

`mlflow-tracing` 3.10.0 (released Feb 2026) is a 1.5 MB pure-Python wheel with 5–8 dependencies. It includes:

- `@mlflow.trace`, `mlflow.start_span()`, `mlflow.get_current_active_span()`
- `mlflow.gemini.autolog()` and all provider autolog integrations
- `mlflow.search_traces()`, `mlflow.set_trace_tag()`, `mlflow.update_current_trace()`
- Async logging and background thread pool export
- `mlflow.flush_trace_async_logging()` for graceful shutdown

It excludes: model registry, tracking UI/server, experiment management, evaluation framework, run management APIs (~1 GB saved).

**Hard rule:** Do NOT co-install `mlflow` and `mlflow-tracing` in the same environment — causes namespace conflicts and version resolution issues.

Use isolated environments by purpose:
- **Server runtime env**: `video-research-mcp[tracing]` (contains `mlflow-tracing`)
- **Local UI helper env**: `mlflow` CLI only (invoked via `uvx --with "mlflow>=3.10.0" ...`)
- **Evaluation env**: `mlflow[genai]>=3.3` (separate from runtime env)

### 5. No-op fallback when MLflow is not installed

```python
try:
    import mlflow
    _available = True
except ImportError:
    _available = False
```

When `_available` is `False`, all tracing decorators become identity functions (zero overhead). Community users who install `video-research-mcp` without `[tracing]` get no MLflow dependency, no import errors, and no performance impact.

### 6. MLflow MCP Server — agent access to traces

MLflow provides a 9-tool MCP server (`mlflow[mcp]>=3.5.1`) that enables Claude Code to query and interact with traces programmatically:

| MCP Tool | Purpose |
|----------|---------|
| `search_traces` | Query traces with filtering, field selection, pagination |
| `get_trace` | Retrieve full trace detail (spans, inputs, outputs, token usage) |
| `delete_traces` | Remove traces by ID or timestamp |
| `set_trace_tag` | Add custom metadata to traces |
| `delete_trace_tag` | Remove trace metadata |
| `log_feedback` | Record evaluation scores (thumbs up/down, structured) |
| `log_expectation` | Log ground truth labels for evaluation |
| `get_assessment` | Fetch assessment details |
| `update_assessment` | Modify existing assessments |

Configuration for Claude Code (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "mlflow": {
      "command": "uv",
      "args": ["run", "--with", "mlflow[mcp]>=3.5.1", "mlflow", "mcp", "run"],
      "env": {
        "MLFLOW_TRACKING_URI": "http://localhost:5000"
      }
    }
  }
}
```

This is what makes Path 2 possible — Claude Code can search for slow traces, read full prompt/response pairs, identify patterns across hundreds of tool calls, and log quality assessments.

### 7. Prompt Registry — versioned prompt management

MLflow 3.x includes `mlflow.genai.register_prompt()` / `mlflow.genai.load_prompt()` for versioned, immutable prompt templates:

- **Immutable versions** with sequential numbering and commit messages
- **Aliases** (`@production`, `@latest`, arbitrary) for blue/green and rollback without code changes
- **Template types**: plain text with `{{variable}}`, chat (role/content dicts), Jinja2 for control flow
- **`model_config` co-versioned** — stores model name, temperature, max_tokens with the prompt
- **`response_format`** — accepts Pydantic model or JSON schema to specify output structure
- **Caching** — immutable versions cached with infinite TTL, alias-based loads with 60s TTL

Relevance for this project: the prompts in `prompts/research.py` and `prompts/content.py` (e.g., `STRUCTURED_EXTRACT`, `DEEP_RESEARCH_SYSTEM`, `SCOPE_DEFINITION`) could be registered as versioned prompts. This decouples prompt iteration from code releases — a prompt alias flip rolls back without redeployment.

**Note:** The Prompt Engineering UI is not yet integrated with the Prompt Registry. The current workflow is: iterate prompts manually → register final version via API.

### 8. GenAI Evaluation — automated quality testing on traces

MLflow 3.x provides evaluation without re-running Gemini calls:

**Offline batch evaluation:**
```python
traces = mlflow.search_traces(
    filter_string=f"timestamp > {int(yesterday.timestamp() * 1000)}"
)
results = mlflow.genai.evaluate(data=traces, scorers=my_scorers)
```

Scorers have access to the full span tree (inputs, outputs, intermediate steps). Built-in scorers:
- `Correctness` — factual correctness against ground truth
- `RetrievalGroundedness` — output grounded in retrieved context
- `RelevanceToQuery` — output addresses the user request
- `Guidelines` — free-text guideline checked by LLM judge
- Custom `@scorer` decorator for code-based checks

**Online automatic evaluation:**
```python
registered_judge = safety_judge.register(name="production_safety_check")
registered_judge.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.1)
)
```

LLM judges run asynchronously against sampled production traffic. Default judge: `openai:/gpt-4.1-mini`, configurable to any provider.

**Human/agent feedback:**
`mlflow.log_feedback()` and `mlflow.log_expectation()` let production applications (or Claude Code via MCP) write quality ratings directly onto traces.

Relevance: collected traces from `video-research-mcp` can be batch-evaluated for structured output quality, groundedness, and schema compliance — without making additional Gemini API calls.

### 9. SpanType mapping for this project

MLflow provides 15 predefined span types via `mlflow.entities.SpanType`. Custom strings are also accepted.

| SpanType | Enum Value | Use in this project |
|----------|-----------|---------------------|
| `TOOL` | `SpanType.TOOL` | Most MCP tool functions (default) |
| `CHAT_MODEL` | `SpanType.CHAT_MODEL` | Set automatically by `gemini.autolog()` |
| `CHAIN` | `SpanType.CHAIN` | `generate_structured()` (LLM call + Pydantic validation) |
| `AGENT` | `SpanType.AGENT` | `research_deep` multi-phase orchestration |
| `RETRIEVER` | `SpanType.RETRIEVER` | YouTube API fetches, `knowledge_search`, Weaviate queries |
| `MEMORY` | `SpanType.MEMORY` | Session operations (`video_create_session`, `video_continue_session`) |
| `PARSER` | `SpanType.PARSER` | `content_extract` (structured output parsing) |

Additional span types available but not directly used: `LLM`, `EMBEDDING`, `RERANKER`, `WORKFLOW`, `TASK`, `GUARDRAIL`, `EVALUATOR`, `UNKNOWN`.

### 10. Async logging and runtime context

**Async logging** via environment variables (preferred for servers):

```bash
MLFLOW_ENABLE_ASYNC_TRACE_LOGGING=true
MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS=20
MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE=2000
MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT=600
```

**Runtime context tagging** via `mlflow.update_current_trace()`:

```python
@mlflow.trace(span_type=SpanType.TOOL)
async def video_analyze(url, instruction, ...):
    mlflow.update_current_trace(tags={
        "tool": "video_analyze",
        "model": get_config().default_model,
        "thinking_level": thinking_level,
    })
```

### 11. No breaking changes in tracing API (2.x → 3.x)

The tracing-specific APIs (`@mlflow.trace`, `mlflow.gemini.autolog()`, spans, tags) did not change between MLflow 2.x and 3.x. Breaking changes in MLflow 3.0 are concentrated in non-tracing areas. Pin `mlflow-tracing>=3.0` safely.

## Rationale: Design Decisions

### Optional dependency, not core

MLflow adds value for developers and power users who want observability. Most community users installing this plugin just want Gemini tools — they should not pay for MLflow in install size, startup time, or complexity. Making it optional via `[tracing]` extra is the right boundary.

### `mlflow-tracing` over full `mlflow`

The full `mlflow` package is ~1 GB with 20+ dependencies. `mlflow-tracing` is 1.5 MB with 5–8 dependencies. Since this is an MCP server (not a training pipeline), there is no need for model registry, artifact storage, or evaluation features. The two packages must not be co-installed.

**Exception:** For evaluation features (`mlflow.genai.evaluate()`), the full `mlflow[genai]>=3.3` package is needed. This is a developer-only activity, not needed in the production trace-collection path.

### `GEMINI_TRACING_ENABLED` over relying solely on install detection

A user might have `mlflow-tracing` installed for another project but not want tracing on this MCP server. The `GEMINI_TRACING_ENABLED=false` env var provides an explicit opt-out independent of package availability.

### Autolog + manual decorators over pure manual instrumentation

Writing manual `start_span()` calls inside `GeminiClient.generate()` would duplicate what `mlflow.gemini.autolog()` already does (and does better — it handles token extraction, error recording, chat history). Manual `@mlflow.trace` decorators on tool functions add the business-logic layer that autolog cannot provide.

### MLflow MCP server as optional companion

The MLflow MCP server is a separate service (not bundled with this plugin) that Claude Code can optionally install. It transforms Claude Code from a blind consumer of this plugin into an active observer — able to diagnose tool failures, identify cost hotspots, and suggest improvements. The setup flow should offer this as an optional step.

### Prompt registry as future optimization path

The prompts in `prompts/*.py` are currently hardcoded strings. Migrating them to the MLflow Prompt Registry would decouple prompt iteration from code releases. However, this is a Phase 2 concern — the initial implementation should focus on trace collection and MCP server integration.

### Retry transparency over retry hiding

The `with_retry()` wrapper around every `generate_content()` call means retry attempts appear as sibling `CHAT_MODEL` spans in the trace tree. This is intentional — it makes retry behavior visible and debuggable.

## Implementation Plan

### Delivery matrix (explicit)

| Path | Primary user | Runtime launcher | MLflow package strategy |
|------|--------------|------------------|-------------------------|
| Source/dev install | Contributors and local developers | `uv run video-research-mcp` | Install `video-research-mcp[tracing]` in project env |
| npx installer | Plugin users | Installer writes MCP entries and env | Interactive choices decide tracing on/off, URI, optional MLflow MCP server |
| uvx MCP runtime | Claude Code consuming plugin | `uvx ... video-research-mcp` | Use plain package by default, switch to traced launcher when opted in |

### Runtime launcher variants (for installer output)

Default (no tracing):
```json
{
  "video-research": {
    "command": "uvx",
    "args": ["video-research-mcp"],
    "env": {
      "GEMINI_API_KEY": "${GEMINI_API_KEY}"
    }
  }
}
```

Tracing enabled:
```json
{
  "video-research": {
    "command": "uvx",
    "args": ["--from", "video-research-mcp[tracing]", "video-research-mcp"],
    "env": {
      "GEMINI_API_KEY": "${GEMINI_API_KEY}",
      "GEMINI_TRACING_ENABLED": "true",
      "MLFLOW_TRACKING_URI": "./mlruns",
      "MLFLOW_EXPERIMENT_NAME": "video-research-mcp"
    }
  }
}
```

### Current architecture (17 tools, 7 sub-servers)

```
server.py (root FastMCP "video-research", _lifespan hook)
├── types.py                  → Literal types + Annotated aliases
├── client.py                 → GeminiClient singleton (generate, generate_structured)
├── config.py                 → ServerConfig from env vars
├── retry.py                  → with_retry() exponential backoff
├── sessions.py               → SessionStore (in-memory, TTL eviction)
├── persistence.py            → SessionDB (SQLite WAL for crash recovery)
├── youtube.py                → YouTubeClient singleton (Data API v3)
├── weaviate_client.py        → WeaviateClient singleton
├── weaviate_store.py         → 8 write-through store functions
├── weaviate_schema.py        → 7 collection definitions
├── tools/video.py            → video_server    (4 tools)
├── tools/youtube.py          → youtube_server  (2 tools)
├── tools/research.py         → research_server (3 tools)
├── tools/content.py          → content_server  (2 tools)
├── tools/search.py           → search_server   (1 tool)
├── tools/infra.py            → infra_server    (2 tools)
└── tools/knowledge.py        → knowledge_server (4 tools)
```

### Phase 1: Core tracing instrumentation

**Goal:** Every tool call and Gemini API call produces a trace with full input/output/token visibility.

#### Files to create/modify

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add `tracing` optional dependency group |
| `src/video_research_mcp/tracing.py` | Create | Guarded imports, `trace()` wrapper, setup/shutdown |
| `src/video_research_mcp/server.py` | Modify | Call `setup_tracing()` / `shutdown_tracing()` in `_lifespan` |
| `src/video_research_mcp/tools/*.py` | Modify | Add `@trace()` to all 17 tool functions |
| `tests/test_tracing.py` | Create | Test both enabled and disabled paths |
| `CLAUDE.md` | Modify | Document tracing env vars and usage |

#### Step 1: Add optional dependency

```toml
# pyproject.toml
[project.optional-dependencies]
tracing = ["mlflow-tracing>=3.0"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.9",
    "mlflow-tracing>=3.0",
]
```

#### Step 2: Create `tracing.py` module (~90 lines)

```python
"""Optional MLflow tracing — no-op when mlflow-tracing is not installed."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.gemini

    _available = True
except ImportError:
    _available = False


def is_tracing_enabled() -> bool:
    """True when mlflow-tracing is installed AND not explicitly disabled."""
    if not _available:
        return False
    return os.getenv("GEMINI_TRACING_ENABLED", "true").lower() not in ("false", "0", "no")


def trace(
    func: Callable | None = None,
    *,
    name: str | None = None,
    span_type: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """Drop-in replacement for @mlflow.trace — identity when tracing is off."""
    if not is_tracing_enabled():
        return func if func is not None else (lambda f: f)
    return mlflow.trace(func, name=name, span_type=span_type, attributes=attributes)


def setup_tracing() -> None:
    """Call once at server startup — sets experiment, enables autolog."""
    if not is_tracing_enabled():
        logger.info("Tracing disabled (mlflow not installed or GEMINI_TRACING_ENABLED=false)")
        return

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "video-research-mcp")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    mlflow.gemini.autolog()
    # mlflow-tracing does not expose mlflow.config.*; async behavior is
    # configured via MLFLOW_ENABLE_ASYNC_TRACE_LOGGING* env vars.
    if hasattr(mlflow, "config") and hasattr(mlflow.config, "enable_async_logging"):
        mlflow.config.enable_async_logging()

    logger.info("Tracing enabled: experiment=%s, uri=%s", experiment, tracking_uri)


def shutdown_tracing() -> None:
    """Call at server shutdown — flushes async trace queue."""
    if not is_tracing_enabled():
        return
    mlflow.flush_trace_async_logging()
    logger.info("Tracing shutdown: flushed pending traces")
```

#### Step 3: Wire into server lifespan

Shutdown order: tracing flush → Weaviate close → Gemini close.

```python
# server.py
from .tracing import setup_tracing, shutdown_tracing

@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Startup/shutdown hook — sets up tracing, tears down shared clients."""
    setup_tracing()
    yield {}
    shutdown_tracing()
    await WeaviateClient.aclose()
    closed = await GeminiClient.close_all()
    logger.info("Lifespan shutdown: closed %d client(s)", closed)
```

#### Step 4: Decorate all 17 tool functions

The `@trace` decorator goes between `@server.tool()` and `async def`:

```python
# tools/video.py
from ..tracing import trace

@video_server.tool(annotations=ToolAnnotations(...))
@trace(name="video_analyze", span_type="TOOL")
async def video_analyze(url, instruction, ...) -> dict:
    ...
```

All 17 tools and their span types:

| Tool | SpanType | Rationale |
|------|----------|-----------|
| `video_analyze` | `TOOL` | Single LLM call with optional cache |
| `video_create_session` | `TOOL` | Creates session + initial LLM analysis |
| `video_continue_session` | `TOOL` | Multi-turn session continuation |
| `video_batch_analyze` | `TOOL` | Concurrent batch of video analyses |
| `video_metadata` | `RETRIEVER` | YouTube API fetch, no LLM |
| `video_playlist` | `RETRIEVER` | YouTube API fetch, no LLM |
| `research_deep` | `AGENT` | Multi-phase orchestration (scope → evidence → synthesis) |
| `research_plan` | `TOOL` | Single structured LLM call |
| `research_assess_evidence` | `TOOL` | Single structured LLM call |
| `content_analyze` | `TOOL` | Single LLM call with URL/file/text input |
| `content_extract` | `PARSER` | Structured extraction with caller schema |
| `web_search` | `TOOL` | Grounded search via Gemini |
| `infra_cache` | `TOOL` | Local cache management, no LLM |
| `infra_configure` | `TOOL` | Config mutation, no LLM |
| `knowledge_search` | `RETRIEVER` | Weaviate hybrid search, no LLM |
| `knowledge_related` | `RETRIEVER` | Weaviate vector search, no LLM |
| `knowledge_stats` | `RETRIEVER` | Weaviate aggregation, no LLM |
| `knowledge_ingest` | `TOOL` | Weaviate insert, no LLM |

#### Step 5: Tests

```python
# tests/test_tracing.py
def test_trace_noop_when_disabled():
    """trace() returns the function unchanged when tracing is disabled."""
    with patch.dict(os.environ, {"GEMINI_TRACING_ENABLED": "false"}):
        @trace(name="test", span_type="TOOL")
        async def my_func():
            return 42

def test_setup_tracing_calls_autolog(mock_mlflow):
    """setup_tracing() enables experiment + autolog for tracing."""
    setup_tracing()
    mock_mlflow.set_tracking_uri.assert_called_once()
    mock_mlflow.set_experiment.assert_called_once()
    mock_mlflow.gemini.autolog.assert_called_once()

def test_setup_tracing_works_without_mlflow_config_namespace(mock_mlflow):
    """mlflow-tracing runtime has no mlflow.config; setup must still succeed."""
    del mock_mlflow.config
    setup_tracing()
    mock_mlflow.gemini.autolog.assert_called_once()
```

### Phase 2: MLflow MCP Server + Claude Code skill

**Goal:** Claude Code can query traces, debug failures, and log quality feedback. A setup flow guides configuration.

#### 2a: Setup flow (in plugin installer)

During `npx video-research-mcp` installation, offer MLflow as an optional feature directly in the Node installer prompts:

```
Step 1: "Enable MLflow tracing for this plugin?" → Yes / No
        Why: visibility into prompts/latency/tokens vs minimal footprint.
        Config: switch MCP launcher to traced uvx command + set GEMINI_TRACING_ENABLED.

Step 2: (if Yes) "Where should traces be stored?"
        → Local path (`./mlruns`) — fastest start, no infra.
        → Remote MLflow URL — shared/team observability.
        Config: set MLFLOW_TRACKING_URI for the video-research MCP server.

Step 3: "Install MLflow MCP server for Claude Code?" → Yes / No
        Why: lets Claude query traces and log feedback directly.
        Config: optionally add `mlflow` MCP server entry.

Step 4: "Enable local UI helper command?" → Yes / No
        Why: optional browser UI for trace browsing without changing runtime deps.
        Config: print and persist helper instructions using isolated `uvx --with mlflow`.

Step 5: Confirm summary and write config
        Output: final launcher args, env vars, and optional MLflow MCP block.
```

Implementation notes:
- For `npx` users, preferences are gathered in `bin/install.js` interactive prompts.
- For local/global plugin installs, values are persisted in generated `.mcp.json` server `env`.
- Precedence at runtime: MCP server `env` in `.mcp.json` > host process env > defaults in code.

#### 2b: Claude Code skill — `mlflow-mcp-traces`

A skill file at `skills/mlflow-mcp-traces.md` that teaches Claude Code:

**What traces capture** — span trees, token usage, input/output text, timing, retry behavior.

**Where to look** — the MLflow MCP server tools and how to use them:
- `search_traces` with filter syntax: `tags.tool = 'research_deep' AND status = 'ERROR'`
- `get_trace` with `extract_fields` for targeted retrieval: `data.spans.*.name`, `info.assessments.*`
- `log_feedback` to record quality observations

**What to look for** — common patterns:
- High token usage: `search_traces` sorted by token count → identify prompts that need trimming
- Slow calls: filter by latency → check if retries or large prompts are the cause
- Failed structured output: find ERROR traces where `generate_structured` spans have validation errors
- Cost attribution: aggregate `mlflow.chat.tokenUsage` across spans to identify expensive tools

**How the tracing architecture works** — the three-layer model (TOOL → retry → CHAT_MODEL), how autolog patches work, where Weaviate store calls appear.

#### 2c: MLflow MCP server installation

Add to `bin/lib/config.js` (the plugin installer's MCP config merger):

```json
{
  "mlflow": {
    "command": "uv",
    "args": ["run", "--with", "mlflow[mcp]>=3.5.1", "mlflow", "mcp", "run"],
    "env": {
      "MLFLOW_TRACKING_URI": "http://localhost:5000"
    }
  }
}
```

This is optional — only installed when the user opts in during setup.

#### 2d: Local UI helper (recommended optional companion)

Do not add full `mlflow` to the server runtime environment. Instead, run MLflow UI in an isolated tool env:

```bash
uvx --with "mlflow>=3.10.0" mlflow ui \
  --backend-store-uri ./mlruns \
  --host 127.0.0.1 \
  --port 5000
```

Expected URL: `http://127.0.0.1:5000`

This keeps runtime lightweight (`mlflow-tracing`) while still giving a first-class local UI path.

### Acceptance Criteria (must pass before rollout)

Install path checks:
- **Source/dev**: server starts with and without `[tracing]`; traces emitted when enabled.
- **uvx runtime**: default launcher runs without MLflow deps; traced launcher emits traces.
- **npx installer**: interactive choices correctly produce launcher args/env and optional mlflow MCP block.

Behavioral checks:
- All 17 tool handlers produce root spans when tracing is enabled.
- Gemini calls appear as child `CHAT_MODEL` spans via autolog.
- Shutdown always calls `mlflow.flush_trace_async_logging()` when tracing is enabled.

Failure-path checks:
- Missing `mlflow-tracing`: server still runs (no-op decorators).
- Invalid/unreachable `MLFLOW_TRACKING_URI`: server logs warning and continues unless explicitly configured to fail fast.
- Missing MLflow MCP server: plugin tools still work; only trace-query capability is absent.

### Phase 3: Evaluation and prompt registry (future)

**Goal:** Automated quality testing on collected traces. Prompt versioning for safe iteration.

#### 3a: Offline evaluation

After traces are collected (Phase 1), developers can run batch evaluations:

```python
import mlflow

traces = mlflow.search_traces(
    experiment_names=["video-research-mcp"],
    filter_string="tags.tool = 'research_deep'"
)
results = mlflow.genai.evaluate(
    data=traces,
    scorers=[
        mlflow.genai.scorers.RetrievalGroundedness(),
        mlflow.genai.scorers.RelevanceToQuery(),
    ]
)
```

**Requires:** `mlflow[genai]>=3.3` (not `mlflow-tracing` — needs the full package for evaluation). This is a developer workstation activity, not part of the production server.

#### 3b: Online evaluation with sampling

For production monitoring, register LLM judges that evaluate sampled traffic:

```python
judge = safety_scorer.register(name="safety_check")
judge.start(
    sampling_config=ScorerSamplingConfig(
        sample_rate=0.1,
        filter_string="tags.tool IN ('research_deep', 'content_analyze')"
    )
)
```

#### 3c: Prompt registry migration

Migrate prompts from `prompts/*.py` to MLflow Prompt Registry:

```python
mlflow.genai.register_prompt(
    name="research-scope-definition",
    template=SCOPE_DEFINITION,
    commit_message="Initial registration from prompts/research.py",
    model_config={
        "model_name": "gemini-3.1-pro-preview",
        "temperature": 1.0,
    },
    tags={"domain": "research", "phase": "scope"},
)
```

Then load in tools: `prompt = mlflow.genai.load_prompt("research-scope-definition@production")`

This decouples prompt iteration from code releases. An alias flip (`@production` → new version) rolls back without redeployment.

**Note:** Prompt Engineering UI integration with the registry is not yet available — iteration is manual via API.

## Environment Variables

### Tracing-specific (new)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_TRACING_ENABLED` | `true` | Enable/disable tracing (independent of mlflow install) |
| `MLFLOW_TRACKING_URI` | `./mlruns` | Where traces are stored (local path or MLflow server URL) |
| `MLFLOW_EXPERIMENT_NAME` | `video-research-mcp` | Experiment name for grouping traces |
| `MLFLOW_ENABLE_ASYNC_TRACE_LOGGING` | `true` | Background thread export (recommended) |
| `MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS` | `20` | Background thread count |
| `MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE` | `2000` | Max buffered traces |
| `MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT` | `600` | Retry window in seconds |

### Existing server env vars (for reference)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Default model |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | Flash model for lightweight tasks |
| `GEMINI_THINKING_LEVEL` | `high` | Default thinking depth |
| `GEMINI_TEMPERATURE` | `1.0` | Default temperature |
| `GEMINI_CACHE_DIR` | `~/.cache/video-research-mcp/` | File cache directory |
| `GEMINI_CACHE_TTL_DAYS` | `30` | Cache time-to-live |
| `GEMINI_MAX_SESSIONS` | `50` | Max concurrent video sessions |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `2` | Session TTL |
| `GEMINI_SESSION_MAX_TURNS` | `24` | Max turns per session |
| `GEMINI_RETRY_MAX_ATTEMPTS` | `3` | Retry attempts for transient errors |
| `GEMINI_RETRY_BASE_DELAY` | `1.0` | Base retry delay (seconds) |
| `GEMINI_RETRY_MAX_DELAY` | `60.0` | Max retry delay (seconds) |
| `YOUTUBE_API_KEY` | `""` | YouTube Data API key (falls back to `GEMINI_API_KEY`) |
| `GEMINI_SESSION_DB` | `""` | SQLite path for session persistence (empty = in-memory) |
| `WEAVIATE_URL` | `""` | Weaviate instance URL (empty = disabled) |
| `WEAVIATE_API_KEY` | `""` | Weaviate API key |

## Usage

### For developers — quick start

```bash
# Install runtime tracing (project env)
uv pip install "video-research-mcp[tracing]"

# Run server — traces stored locally by default
GEMINI_API_KEY=... uv run video-research-mcp

# Optional local UI (isolated env, does not modify runtime env)
uvx --with "mlflow>=3.10.0" mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000

# Run with remote server
MLFLOW_TRACKING_URI=http://mlflow:5000 GEMINI_API_KEY=... uv run video-research-mcp

# Disable tracing
GEMINI_TRACING_ENABLED=false GEMINI_API_KEY=... uv run video-research-mcp
```

### For Claude Code — with MCP server

```bash
# Install plugin as usual
npx video-research-mcp@latest

# During setup, choose tracing/local-vs-remote URI/optional MLflow MCP server/local UI helper
# Claude Code can then use /gr:search, /gr:video etc. AND query traces via MLflow MCP tools
```

### Offline evaluation (developer workstation)

```bash
# Requires full mlflow in a separate env, not in runtime tracing env
uvx --with "mlflow[genai]>=3.3" python -c "import mlflow; print(mlflow.__version__)"

# Run evaluation on collected traces
uvx --with "mlflow[genai]>=3.3" python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
traces = mlflow.search_traces(experiment_names=['video-research-mcp'])
results = mlflow.genai.evaluate(data=traces, scorers=[...])
print(results.tables['eval_results'])
"
```

## Sources

- [MLflow Tracing Overview](https://mlflow.org/docs/latest/genai/tracing/)
- [MLflow Manual Tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/)
- [MLflow Gemini Integration](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/gemini/)
- [mlflow-tracing on PyPI](https://pypi.org/project/mlflow-tracing/) — v3.10.0, Feb 2026
- [Lightweight Tracing SDK](https://mlflow.org/docs/latest/genai/tracing/lightweight-sdk/)
- [SpanType Reference](https://mlflow.org/docs/latest/genai/concepts/span/)
- [MLflow MCP Server](https://mlflow.org/docs/latest/genai/mcp/) — 9 tools, requires `mlflow[mcp]>=3.5.1`
- [MLflow Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/)
- [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/genai/eval/)
- [MLflow Production Monitoring](https://mlflow.org/docs/latest/genai/tracing/production-monitoring/)
- [MLflow 3.0 Migration Guide](https://mlflow.org/docs/latest/migration/v3/)
- [Tracing FAQ](https://mlflow.org/docs/latest/genai/tracing/faq/)
