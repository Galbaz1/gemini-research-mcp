# Architecture Guide

Technical reference for the `video-research-mcp` codebase. Covers the system design, component interactions, and conventions that govern every module.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Composite Server Pattern](#2-composite-server-pattern)
3. [GeminiClient Pipeline](#3-geminiclient-pipeline)
4. [Tool Conventions](#4-tool-conventions)
5. [Tool Reference (18 tools)](#5-tool-reference-18-tools)
6. [Singletons](#6-singletons)
7. [Weaviate Integration](#7-weaviate-integration)
8. [Session Management](#8-session-management)
9. [Caching](#9-caching)
10. [Configuration](#10-configuration)
11. [URL Validation](#11-url-validation)
12. [Error Handling](#12-error-handling)
13. [Prompt Templates](#13-prompt-templates)

---

## 1. System Overview

`video-research-mcp` is an MCP (Model Context Protocol) server that exposes 18 tools for video analysis, deep research, content extraction, web search, and knowledge management. It communicates over **stdio transport** using **FastMCP** (`fastmcp>=2.0`) and is powered by **Gemini 3.1 Pro** via the `google-genai` SDK.

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp>=2.0` | MCP server framework (FastMCP 3.x) |
| `google-genai>=1.0` | Gemini API client (generate, structured output, File API) |
| `google-api-python-client>=2.100` | YouTube Data API v3 |
| `pydantic>=2.0` | Schema validation, structured output models |
| `weaviate-client>=4.19.2` | Vector database for knowledge persistence |

### Build & Runtime

- **Build backend**: hatchling
- **Python**: >= 3.11
- **Entry point**: `video-research-mcp` console script -> `server.py:main()`
- **Lint**: ruff (line-length=100, target py311)
- **Tests**: pytest with `asyncio_mode=auto`

### Source Layout

```
src/video_research_mcp/
  server.py              Root FastMCP app, mounts 7 sub-servers
  client.py              GeminiClient singleton (client pool)
  config.py              ServerConfig from env vars, runtime update
  sessions.py            In-memory SessionStore with TTL eviction
  persistence.py         SQLite-backed session persistence (WAL mode)
  cache.py               File-based JSON analysis cache
  errors.py              Structured error handling (ToolError, categorize_error)
  types.py               Shared Literal types + Annotated aliases
  youtube.py             YouTubeClient singleton (Data API v3)
  retry.py               Exponential backoff for transient Gemini errors
  weaviate_client.py     WeaviateClient singleton
  weaviate_schema.py     7 collection definitions (dataclass-based)
  weaviate_store.py      Write-through store functions (one per collection)
  models/
    video.py             VideoResult, SessionInfo, SessionResponse
    video_batch.py       BatchVideoItem, BatchVideoResult
    research.py          Finding, ResearchReport, ResearchPlan, EvidenceAssessment
    content.py           ContentResult
    youtube.py           VideoMetadata, PlaylistInfo
    knowledge.py         KnowledgeHit, KnowledgeSearchResult, KnowledgeStatsResult
  prompts/
    research.py          Deep research system prompt + phase templates
    content.py           STRUCTURED_EXTRACT template
  tools/
    video.py             video_server (4 tools)
    video_core.py        Shared analysis pipeline (cache + Gemini + cache save)
    video_url.py         YouTube URL validation + Content builder
    video_file.py        Local video file handling, File API upload
    youtube.py           youtube_server (2 tools)
    research.py          research_server (3 tools)
    content.py           content_server (2 tools)
    search.py            search_server (1 tool)
    infra.py             infra_server (2 tools)
    knowledge.py         knowledge_server (4 tools)
```

**Tool count**: 4 + 2 + 3 + 2 + 1 + 2 + 4 = **18 tools** across 7 sub-servers.

---

## 2. Composite Server Pattern

The server uses FastMCP's **mount** pattern to compose a root server from independent sub-servers. Each sub-server owns a domain and registers its own tools.

### Root Server (`server.py`)

```python
app = FastMCP("video-research", instructions="...", lifespan=_lifespan)

app.mount(video_server)       # tools/video.py       4 tools
app.mount(research_server)    # tools/research.py     3 tools
app.mount(content_server)     # tools/content.py      2 tools
app.mount(search_server)      # tools/search.py       1 tool
app.mount(infra_server)       # tools/infra.py        2 tools
app.mount(youtube_server)     # tools/youtube.py      2 tools
app.mount(knowledge_server)   # tools/knowledge.py    4 tools
#                                                     ── 18 tools total
```

### Lifespan Hook

The `_lifespan` async context manager handles graceful shutdown:

1. **Weaviate**: `WeaviateClient.aclose()` closes the cluster connection
2. **Gemini**: `GeminiClient.close_all()` tears down all pooled clients

```python
@asynccontextmanager
async def _lifespan(server: FastMCP):
    yield {}
    await WeaviateClient.aclose()
    closed = await GeminiClient.close_all()
```

The lifespan runs at server startup (before `yield`) and shutdown (after `yield`). No startup work is needed -- all singletons lazy-initialize on first use.

### Sub-Server Independence

Each sub-server is a standalone `FastMCP` instance:

```python
# tools/research.py
research_server = FastMCP("research")

@research_server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def research_deep(topic: TopicParam, ...) -> dict:
    ...
```

Sub-servers share singletons (`GeminiClient`, `get_config()`, `session_store`) via imports from the parent package. They never import from each other.

---

## 3. GeminiClient Pipeline

`GeminiClient` (`client.py`) is a process-wide client pool keyed by API key. It provides two generation entry points that all tools funnel through.

### Client Pool

```
GeminiClient._clients: dict[str, genai.Client]
```

`GeminiClient.get(api_key=None)` returns (or creates) a `genai.Client` for the given key. Default key comes from `get_config().gemini_api_key` or `GEMINI_API_KEY` env var.

### `generate()` -- Raw Text Output

```python
async def generate(
    contents,
    *,
    model=None,
    thinking_level=None,
    response_schema=None,   # dict -> response_json_schema
    temperature=None,
    system_instruction=None,
    tools=None,             # e.g. [GoogleSearch(), UrlContext()]
) -> str
```

Builds a `GenerateContentConfig` with:
- **ThinkingConfig**: resolved from param or config default
- **Temperature**: param or config default
- **response_json_schema**: set when `response_schema` dict is provided
- **system_instruction**: optional system prompt
- **tools**: Gemini tool wiring (GoogleSearch, UrlContext)

Calls `client.aio.models.generate_content()` wrapped in `with_retry()` for exponential backoff. Strips thinking parts from the response -- only returns user-visible text.

### `generate_structured()` -- Validated Pydantic Output

```python
async def generate_structured(
    contents,
    *,
    schema: type[BaseModel],
    ...
) -> BaseModel
```

Delegates to `generate()` with `response_schema=schema.model_json_schema()`, then validates via `schema.model_validate_json(raw)`. This is the primary output path for tools that use default schemas.

### Pipeline Flow

```
Tool function
  -> GeminiClient.generate_structured(contents, schema=VideoResult)
     -> GeminiClient.generate(contents, response_schema=VideoResult.model_json_schema())
        -> with_retry(client.aio.models.generate_content(...))
        -> strip thinking parts
        -> return raw text
     -> VideoResult.model_validate_json(raw)
     -> return validated Pydantic model
  -> model.model_dump() -> dict
```

For custom `output_schema` (caller-provided JSON Schema):
```
Tool function
  -> GeminiClient.generate(contents, response_schema=custom_dict)
     -> (same pipeline)
     -> return raw JSON text
  -> json.loads(raw) -> dict
```

### Retry Mechanism (`retry.py`)

`with_retry(coro_factory)` wraps any async callable with exponential backoff:

- **Retryable patterns**: `429`, `quota`, `resource_exhausted`, `timeout`, `503`, `service unavailable`
- **Backoff**: `base_delay * 2^attempt + jitter`, capped at `max_delay`
- **Config**: `retry_max_attempts` (default 3), `retry_base_delay` (1.0s), `retry_max_delay` (60s)
- **Non-retryable errors**: raised immediately

---

## 4. Tool Conventions

Every tool follows a strict set of conventions enforced across the codebase.

### Required Decorators

Every tool MUST have `ToolAnnotations`:

```python
@server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,      # Does not modify external state
        destructiveHint=False,   # Does not delete data
        idempotentHint=True,     # Same input -> same output
        openWorldHint=True,      # Accesses external APIs
    )
)
```

### Parameter Typing

Parameters use `Annotated` with `Field` constraints:

```python
async def my_tool(
    query: Annotated[str, Field(min_length=2, description="Search query")],
    limit: Annotated[int, Field(ge=1, le=100, description="Max results")] = 10,
    thinking_level: ThinkingLevel = "medium",
) -> dict:
```

Shared type aliases live in `types.py`:

| Alias | Type | Constraints |
|-------|------|-------------|
| `ThinkingLevel` | `Literal["minimal", "low", "medium", "high"]` | -- |
| `Scope` | `Literal["quick", "moderate", "deep", "comprehensive"]` | -- |
| `CacheAction` | `Literal["stats", "list", "clear"]` | -- |
| `ModelPreset` | `Literal["best", "stable", "budget"]` | -- |
| `KnowledgeCollection` | `Literal[7 collection names]` | -- |
| `YouTubeUrl` | `Annotated[str, ...]` | `min_length=10` |
| `TopicParam` | `Annotated[str, ...]` | `min_length=3, max_length=500` |
| `VideoFilePath` | `Annotated[str, ...]` | `min_length=1` |
| `VideoDirectoryPath` | `Annotated[str, ...]` | `min_length=1` |
| `PlaylistUrl` | `Annotated[str, ...]` | `min_length=10` |

### Instruction-Driven Design

Tools accept an `instruction` parameter (free text) instead of fixed modes. The LLM client writes the instruction, Gemini returns structured JSON:

```python
video_analyze(url="...", instruction="List all recipes and ingredients shown")
video_analyze(url="...", instruction="Extract every CLI command demonstrated")
content_analyze(url="https://arxiv.org/...", instruction="Extract the methodology section")
```

### Custom Output Schemas

Tools accept an optional `output_schema` dict (JSON Schema) for caller-defined response shapes. When provided, `generate()` is called with `response_schema=output_schema` instead of the default Pydantic model:

```python
video_analyze(
    url="...",
    instruction="List recipes",
    output_schema={"type": "object", "properties": {"recipes": {"type": "array"}}}
)
```

### Error Convention

Tools **never raise** -- they catch all exceptions and return a `make_tool_error()` dict:

```python
try:
    result = await GeminiClient.generate_structured(...)
    return result.model_dump()
except Exception as exc:
    return make_tool_error(exc)
```

### Docstrings

Every tool has a docstring with `Args:` and `Returns:` sections.

### Write-Through to Weaviate

When Weaviate is configured (`WEAVIATE_URL`), every result-producing tool automatically stores its output via a `store_*` function from `weaviate_store.py`. This is the primary mechanism for building the knowledge base -- it requires no action from the MCP client.

**Pattern**: import the store function inside the tool, call after the result is ready:

```python
result = model_result.model_dump()
from ..weaviate_store import store_video_analysis
await store_video_analysis(result, content_id, instruction, source_label)
return result
```

**Tool-to-collection mapping**:

| Tool | Store Function | Collection |
|------|---------------|------------|
| `video_analyze` | `store_video_analysis` | `VideoAnalyses` |
| `video_batch_analyze` | `store_video_analysis` (per file) | `VideoAnalyses` |
| `video_continue_session` | `store_session_turn` | `SessionTranscripts` |
| `video_metadata` | `store_video_metadata` | `VideoMetadata` |
| `research_deep` | `store_research_finding` | `ResearchFindings` |
| `research_plan` | `store_research_plan` | `ResearchPlans` |
| `research_assess_evidence` | `store_evidence_assessment` | `ResearchFindings` |
| `content_analyze` | `store_content_analysis` | `ContentAnalyses` |
| `web_search` | `store_web_search` | `WebSearchResults` |

Tools not in this table (`content_extract`, `video_playlist`, `infra_cache`, `infra_configure`, and the 4 knowledge tools) do not write through.

**Key guarantees**:
- **Non-fatal**: All store functions catch exceptions and log warnings. Tool results are never lost due to Weaviate failures.
- **Guard check**: `_is_enabled()` returns immediately when `weaviate_enabled` is `False`.
- **New tool convention**: When adding a tool that produces analytical results, add a corresponding `store_*` function to `weaviate_store.py` and call it from the tool.

---

## 5. Tool Reference (18 tools)

### Video Server (4 tools)

**`video_analyze`** -- Analyze a video with any instruction.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `YouTubeUrl \| None` | `None` | YouTube URL (mutually exclusive with `file_path`) |
| `file_path` | `VideoFilePath \| None` | `None` | Local video path |
| `instruction` | `str` | comprehensive analysis | What to analyze |
| `output_schema` | `dict \| None` | `None` | Custom JSON Schema |
| `thinking_level` | `ThinkingLevel` | `"high"` | Gemini thinking depth |
| `use_cache` | `bool` | `True` | Use cached results |

Returns: `VideoResult` dict (or custom schema). Caches results. Writes to `VideoAnalyses` collection.

**`video_create_session`** -- Create a persistent session for multi-turn video exploration.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `YouTubeUrl \| None` | `None` | YouTube URL |
| `file_path` | `VideoFilePath \| None` | `None` | Local video path |
| `description` | `str` | `""` | Session purpose |

Returns: `SessionInfo` dict with `session_id`. Fetches video title via YouTube API or Gemini fallback.

**`video_continue_session`** -- Continue analysis within an existing session.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `session_id` | `str` | (required) | Session ID from `video_create_session` |
| `prompt` | `str` | (required) | Follow-up question |

Returns: `SessionResponse` dict with `response` and `turn_count`. Appends to session history. Writes to `SessionTranscripts`.

**`video_batch_analyze`** -- Analyze all video files in a directory concurrently.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `directory` | `VideoDirectoryPath` | (required) | Directory path |
| `instruction` | `str` | comprehensive analysis | What to analyze |
| `glob_pattern` | `str` | `"*"` | File filter glob |
| `output_schema` | `dict \| None` | `None` | Custom JSON Schema |
| `thinking_level` | `ThinkingLevel` | `"high"` | Gemini thinking depth |
| `max_files` | `int` | `20` | Max files (1-50) |

Returns: `BatchVideoResult` dict. Uses semaphore-bounded concurrency (3 parallel Gemini calls).

### YouTube Server (2 tools)

**`video_metadata`** -- Fetch YouTube video metadata without Gemini.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `YouTubeUrl` | (required) | YouTube URL |

Returns: `VideoMetadata` dict (title, stats, duration, tags, channel). Costs 1 YouTube API unit, 0 Gemini units. Writes to `VideoMetadata` collection with deterministic UUID.

**`video_playlist`** -- Get video items from a YouTube playlist.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `PlaylistUrl` | (required) | YouTube playlist URL |
| `max_items` | `int` | `20` | Max items (1-50) |

Returns: `PlaylistInfo` dict. Costs 1 YouTube API unit per page.

### Research Server (3 tools)

**`research_deep`** -- Run multi-phase deep research with evidence-tier labeling.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `topic` | `TopicParam` | (required) | Research question |
| `scope` | `Scope` | `"moderate"` | Research depth |
| `thinking_level` | `ThinkingLevel` | `"high"` | Gemini thinking depth |

Pipeline: Scope Definition (unstructured) -> Evidence Collection (structured, `FindingsContainer`) -> Synthesis (structured, `ResearchSynthesis`) -> `ResearchReport`.

Every claim is labeled: CONFIRMED, STRONG INDICATOR, INFERENCE, SPECULATION, or UNKNOWN. Writes findings to `ResearchFindings`.

**`research_plan`** -- Generate a multi-agent research orchestration plan.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `topic` | `TopicParam` | (required) | Research question |
| `scope` | `Scope` | `"moderate"` | Research depth |
| `available_agents` | `int` | `10` | Agent count (1-50) |

Returns: `ResearchPlan` dict with phases, task decomposition, model assignments. Does NOT spawn agents -- provides the blueprint. Falls back to unstructured generate on structured output failure. Writes to `ResearchPlans`.

**`research_assess_evidence`** -- Assess a claim against sources.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `claim` | `str` | (required) | Statement to verify |
| `sources` | `list[str]` | (required) | Evidence sources |
| `context` | `str` | `""` | Additional context |

Returns: `EvidenceAssessment` dict with tier, confidence (0-1), reasoning. Writes to `ResearchFindings`.

### Content Server (2 tools)

**`content_analyze`** -- Analyze content (file, URL, or text) with any instruction.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `instruction` | `str` | comprehensive analysis | What to analyze |
| `file_path` | `str \| None` | `None` | Local file (PDF or text) |
| `url` | `str \| None` | `None` | URL to analyze |
| `text` | `str \| None` | `None` | Raw text content |
| `output_schema` | `dict \| None` | `None` | Custom JSON Schema |
| `thinking_level` | `ThinkingLevel` | `"medium"` | Gemini thinking depth |

Exactly one source required. URL path uses `UrlContext()` tool wiring with two-step fallback (fetch unstructured, then reshape). Writes to `ContentAnalyses`.

**`content_extract`** -- Extract structured data using a JSON Schema.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `content` | `str` | (required) | Source text |
| `schema` | `dict` | (required) | JSON Schema for extraction |

Returns: dict matching the provided schema. Uses `STRUCTURED_EXTRACT` prompt template.

### Search Server (1 tool)

**`web_search`** -- Search the web using Gemini's Google Search grounding.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `str` | (required) | Search terms |
| `num_results` | `int` | `5` | Results count (1-20) |

Uses the flash model with `GoogleSearch()` tool wiring. Returns query, response text, and grounding sources (title + URL). Writes to `WebSearchResults`.

### Infra Server (2 tools)

**`infra_cache`** -- Manage the analysis cache.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `action` | `CacheAction` | `"stats"` | `"stats"`, `"list"`, or `"clear"` |
| `content_id` | `str \| None` | `None` | Scope clear to specific ID |

Returns: cache statistics, entry list, or removed count depending on action.

**`infra_configure`** -- Reconfigure the server at runtime.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `preset` | `ModelPreset \| None` | `None` | `"best"`, `"stable"`, or `"budget"` |
| `model` | `str \| None` | `None` | Model ID override (takes precedence) |
| `thinking_level` | `ThinkingLevel \| None` | `None` | Thinking depth |
| `temperature` | `float \| None` | `None` | Sampling temp (0.0-2.0) |

Changes take effect immediately. Returns current config, active preset, and available presets.

### Knowledge Server (4 tools)

All knowledge tools gracefully degrade when Weaviate is not configured (return empty results, not errors).

**`knowledge_search`** -- Hybrid search across knowledge collections.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `str` | (required) | Search query |
| `collections` | `list[KnowledgeCollection] \| None` | `None` | Collections to search (all if omitted) |
| `limit` | `int` | `10` | Max results per collection (1-100) |
| `alpha` | `float` | `0.5` | 0=BM25, 1=vector, 0.5=hybrid |

Returns: `KnowledgeSearchResult` with merged, score-sorted results.

**`knowledge_related`** -- Find semantically related objects via near-object vector search.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `object_id` | `str` | (required) | Source object UUID |
| `collection` | `KnowledgeCollection` | (required) | Source collection |
| `limit` | `int` | `5` | Max related results (1-50) |

Returns: `KnowledgeRelatedResult` with related hits sorted by distance.

**`knowledge_stats`** -- Get object counts per collection.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `collection` | `KnowledgeCollection \| None` | `None` | Single collection or all |

Returns: `KnowledgeStatsResult` with per-collection counts and total.

**`knowledge_ingest`** -- Manually insert data into a knowledge collection.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `collection` | `KnowledgeCollection` | (required) | Target collection |
| `properties` | `dict` | (required) | Object properties |

Validates properties against the collection schema -- unknown keys are rejected. Returns: `KnowledgeIngestResult` with object UUID.

---

## 6. Singletons

Five singletons provide shared state across the server.

### GeminiClient (`client.py`)

**Pattern**: Class-level dict pool, one `genai.Client` per API key.

```python
GeminiClient._clients: dict[str, genai.Client]
```

- `get(api_key=None)` -- lazy-creates and caches clients
- `generate()` -- text output with thinking + optional structured schema
- `generate_structured()` -- validated Pydantic output
- `close_all()` -- tears down all clients (called at lifespan shutdown)

### ServerConfig (`config.py`)

**Pattern**: Module-level `_config` variable, lazy-initialized by `get_config()`.

- `get_config()` -- returns the singleton, creating from env vars on first call
- `update_config(**overrides)` -- patches the live config (used by `infra_configure`)
- Not thread-safe for writes, but acceptable for a single-process MCP server

### SessionStore (`sessions.py`)

**Pattern**: Module-level `session_store` singleton.

- In-memory `dict[str, VideoSession]` with optional SQLite backing
- TTL eviction on every `create()` and `get()` call
- Bounded history trimming (`session_max_turns * 2` items)
- LRU eviction when `max_sessions` is reached

### YouTubeClient (`youtube.py`)

**Pattern**: Class-level `_service` singleton (lazy via `get()`).

- Built with `googleapiclient.discovery.build("youtube", "v3", ...)`
- Uses `YOUTUBE_API_KEY` with fallback to `GEMINI_API_KEY`
- Sync API wrapped in `asyncio.to_thread()` for all methods
- `reset()` for testing

### WeaviateClient (`weaviate_client.py`)

**Pattern**: Module-level `_client` variable, thread-safe via `threading.Lock`.

- `get()` -- connects and ensures schema collections exist (idempotent)
- `is_available()` -- checks if configured and reachable
- `close()` / `aclose()` -- tears down the connection
- `reset()` -- clears singleton state for testing
- Supports WCS cloud, local instances, and custom deployments via URL detection

---

## 7. Weaviate Integration

The knowledge layer uses Weaviate as a vector database for persistent, searchable storage of all tool outputs.

### Architecture

```
Tool produces result
  -> weaviate_store.store_*()     # write-through (non-fatal)
     -> WeaviateClient.get()      # lazy connect + schema ensure
        -> weaviate_schema.py     # 7 collection definitions
     -> collection.data.insert()  # async via to_thread
```

### Client (`weaviate_client.py`)

`WeaviateClient.get()` auto-detects the deployment type from the URL:

| URL Pattern | Connection Method |
|-------------|-------------------|
| `http://localhost:*`, `http://127.0.0.1:*` | `connect_to_local(host, port, grpc_port=port+1)` |
| `https://*.weaviate.network` | `connect_to_weaviate_cloud(url, auth)` |
| Other | `connect_to_custom(host, port, grpc_host, grpc_port)` |

On first connection, `ensure_collections()` iterates all 7 `CollectionDef` objects and creates any that don't exist. This is idempotent -- existing collections are skipped.

### Schema (`weaviate_schema.py`)

Seven collections, each defined as a `CollectionDef` dataclass:

| Collection | Source Tool(s) | Vectorized Fields |
|------------|---------------|-------------------|
| `ResearchFindings` | `research_deep`, `research_assess_evidence` | topic, claim, reasoning, executive_summary |
| `VideoAnalyses` | `video_analyze`, `video_batch_analyze` | instruction, title, summary, key_points |
| `ContentAnalyses` | `content_analyze` | instruction, title, summary, key_points, entities |
| `VideoMetadata` | `video_metadata` | title, description, tags |
| `SessionTranscripts` | `video_continue_session` | video_title, turn_prompt, turn_response |
| `WebSearchResults` | `web_search` | query, response |
| `ResearchPlans` | `research_plan` | topic, task_decomposition |

Every collection includes common properties:
- `created_at` (date, skip vectorization)
- `source_tool` (text, skip vectorization)

Fields marked `skip_vectorization=True` are stored but not included in the vector embedding (IDs, timestamps, raw JSON blobs).

### Write-Through Store (`weaviate_store.py`)

One async function per collection, all following the same pattern:

```python
async def store_video_analysis(result, content_id, instruction, source_url=""):
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoAnalyses")
            return str(collection.data.insert(properties={...}))
        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
```

Key design decisions:
- **Non-fatal**: All store functions catch exceptions and log warnings. Tool results are never lost due to Weaviate failures.
- **Guard function**: `_is_enabled()` checks `get_config().weaviate_enabled` before any Weaviate call.
- **Thread offloading**: Weaviate's sync client is wrapped in `asyncio.to_thread()` to avoid blocking the event loop.
- **Deterministic UUIDs**: `store_video_metadata` uses `weaviate.util.generate_uuid5(video_id)` for deduplication -- repeated metadata fetches for the same video update rather than duplicate.

### Knowledge Tools (`tools/knowledge.py`)

Four tools provide read/write access to the knowledge store:
- `knowledge_search` -- hybrid search (BM25 + vector) across any/all collections
- `knowledge_related` -- near-object vector search for semantic similarity
- `knowledge_stats` -- object counts per collection
- `knowledge_ingest` -- manual insert with property validation

All tools gracefully degrade when `weaviate_enabled` is `False` (return empty result models, not errors).

---

## 8. Session Management

Sessions enable multi-turn video conversations where the model retains context across prompts.

### In-Memory Store (`sessions.py`)

`SessionStore` holds a `dict[str, VideoSession]`:

```python
@dataclass
class VideoSession:
    session_id: str           # 12-char hex UUID prefix
    url: str                  # YouTube URL or File API URI
    mode: str                 # always "general"
    video_title: str
    history: list[Content]    # Gemini Content objects (user + model pairs)
    created_at: datetime
    last_active: datetime
    turn_count: int
```

### Lifecycle

1. **Create**: `video_create_session` -> `session_store.create(url, mode, title)`
   - Evicts expired sessions (TTL = `session_timeout_hours`)
   - If at `max_sessions`, evicts the least-recently-active session
   - Returns a 12-char hex session ID

2. **Continue**: `video_continue_session` -> `session_store.get(id)` + `add_turn()`
   - Rebuilds the full conversation: `session.history + [new_user_content]`
   - Sends to Gemini with the complete history
   - Appends both user and model content to history
   - Trims history to `session_max_turns * 2` items (sliding window)

3. **Expiry**: Sessions expire after `session_timeout_hours` of inactivity (checked on every `create()` and `get()` call)

### SQLite Persistence (`persistence.py`)

When `GEMINI_SESSION_DB` is set, `SessionStore` delegates to `SessionDB`:

- **WAL mode**: `PRAGMA journal_mode=WAL` for concurrent reads and fast writes
- **Synchronous NORMAL**: trades durability for speed (appropriate for session data)
- **Write-through**: every `create()` and `add_turn()` immediately saves to SQLite
- **Read-through**: `get()` checks memory first, falls back to SQLite, and caches in memory

Content serialization:
- `_content_to_dict()` converts `genai.Content` -> JSON-safe dict (handles `text`, `file_data`, `thought` parts)
- `_dict_to_content()` deserializes back to `genai.Content`

### Local Video Sessions

When a session is created with a local video file:
1. The file is uploaded to Gemini's File API (regardless of size)
2. The returned `file_uri` becomes the session's URL
3. All subsequent turns reference this URI

This ensures the file is available for multi-turn replay without re-uploading.

---

## 9. Caching

The file-based JSON cache (`cache.py`) stores tool results on disk to avoid redundant Gemini API calls.

### Key Structure

```
{content_id}_{tool_name}_{instruction_hash}_{model_hash}.json
```

- **content_id**: YouTube video ID or file SHA-256 prefix
- **tool_name**: e.g. `video_analyze`
- **instruction_hash**: MD5 of instruction text (8 hex chars), or `"default"`
- **model_hash**: MD5 of model ID (8 hex chars)

The instruction hash differentiates results for the same content analyzed with different instructions.

### Cache Directory

Default: `~/.cache/video-research-mcp/`. Configurable via `GEMINI_CACHE_DIR`.

### Operations

| Function | Description |
|----------|-------------|
| `load()` | Return cached dict or `None` if miss/expired |
| `save()` | Write analysis dict wrapped in metadata envelope |
| `clear()` | Remove cache files (all or by content_id) |
| `stats()` | Return file count, total size, TTL |
| `list_entries()` | List all cached entries with metadata |

### Envelope Format

```json
{
  "cached_at": "2026-02-27T10:30:00",
  "content_id": "dQw4w9WgXcQ",
  "tool": "video_analyze",
  "model": "gemini-3.1-pro-preview",
  "analysis": { ... }
}
```

### TTL

Cache files are checked by modification time. Files older than `cache_ttl_days` (default 30) are treated as misses. No background cleanup -- expired files are only detected on `load()`.

### Integration with Tools

Only `video_analyze` and `video_batch_analyze` use the cache (via `video_core.py`):

```python
# Check cache
cached = cache_load(content_id, "video_analyze", cfg.default_model, instruction=instruction)
if cached:
    cached["cached"] = True
    return cached

# ... Gemini call ...

# Save to cache
cache_save(content_id, "video_analyze", cfg.default_model, result, instruction=instruction)
```

Cached results include a `"cached": True` flag so callers can distinguish cache hits.

---

## 10. Configuration

### ServerConfig (`config.py`)

All configuration is resolved from environment variables via `ServerConfig.from_env()`:

| Env Variable | Field | Default | Validation |
|-------------|-------|---------|------------|
| `GEMINI_API_KEY` | `gemini_api_key` | `""` (required at runtime) | -- |
| `GEMINI_MODEL` | `default_model` | `gemini-3.1-pro-preview` | -- |
| `GEMINI_FLASH_MODEL` | `flash_model` | `gemini-3-flash-preview` | -- |
| `GEMINI_THINKING_LEVEL` | `default_thinking_level` | `high` | Must be in `{minimal, low, medium, high}` |
| `GEMINI_TEMPERATURE` | `default_temperature` | `1.0` | -- |
| `GEMINI_CACHE_DIR` | `cache_dir` | `~/.cache/video-research-mcp/` | -- |
| `GEMINI_CACHE_TTL_DAYS` | `cache_ttl_days` | `30` | >= 1 |
| `GEMINI_MAX_SESSIONS` | `max_sessions` | `50` | >= 1 |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `session_timeout_hours` | `2` | >= 1 |
| `GEMINI_SESSION_MAX_TURNS` | `session_max_turns` | `24` | >= 1 |
| `GEMINI_RETRY_MAX_ATTEMPTS` | `retry_max_attempts` | `3` | >= 1 |
| `GEMINI_RETRY_BASE_DELAY` | `retry_base_delay` | `1.0` | > 0 |
| `GEMINI_RETRY_MAX_DELAY` | `retry_max_delay` | `60.0` | > 0 |
| `YOUTUBE_API_KEY` | `youtube_api_key` | `""` | Falls back to `GEMINI_API_KEY` |
| `GEMINI_SESSION_DB` | `session_db_path` | `""` | Empty = in-memory only |
| `WEAVIATE_URL` | `weaviate_url` | `""` | -- |
| `WEAVIATE_API_KEY` | `weaviate_api_key` | `""` | -- |
| -- | `weaviate_enabled` | derived | `True` if `WEAVIATE_URL` is set |

### Model Presets

Three presets are available via `infra_configure`:

| Preset | Default Model | Flash Model | Description |
|--------|---------------|-------------|-------------|
| `best` | `gemini-3.1-pro-preview` | `gemini-3-flash-preview` | Max quality (lowest rate limits) |
| `stable` | `gemini-3-pro-preview` | `gemini-3-flash-preview` | Fallback (higher rate limits) |
| `budget` | `gemini-3-flash-preview` | `gemini-3-flash-preview` | Cost-optimized (highest rate limits) |

### Runtime Updates

`update_config(**overrides)` patches the live singleton:

```python
cfg = get_config()                    # current config
data = cfg.model_dump()               # to dict
data.update({k: v for k, v in overrides.items() if v is not None})
_config = ServerConfig(**data)        # re-validate via Pydantic
```

Changes take effect immediately for all subsequent tool calls. The API key is excluded from `infra_configure` output for security.

---

## 11. URL Validation

YouTube URL validation (`tools/video_url.py`) prevents spoofed domains and extracts video IDs from all legitimate YouTube URL formats.

### Host Validation

```python
def _is_youtube_host(host: str) -> bool:
    # Matches: youtube.com, www.youtube.com, m.youtube.com, music.youtube.com
    return host == "youtube.com" or host.endswith(".youtube.com")

def _is_youtu_be_host(host: str) -> bool:
    # Matches: youtu.be, www.youtu.be
    return host == "youtu.be" or host == "www.youtu.be"
```

Host matching is case-insensitive and strips port numbers.

### Supported URL Formats

| Format | Example |
|--------|---------|
| Standard watch | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Short link | `https://youtu.be/dQw4w9WgXcQ` |
| Shorts | `https://www.youtube.com/shorts/dQw4w9WgXcQ` |
| Embed | `https://www.youtube.com/embed/dQw4w9WgXcQ` |
| Live | `https://www.youtube.com/live/dQw4w9WgXcQ` |
| Mobile | `https://m.youtube.com/watch?v=dQw4w9WgXcQ` |
| Music | `https://music.youtube.com/watch?v=dQw4w9WgXcQ` |
| With playlist | `https://www.youtube.com/watch?v=xxx&list=PLxxx` |

### Normalization

All URLs are normalized to `https://www.youtube.com/watch?v=VIDEO_ID`:
- Backslashes are stripped
- Video ID is extracted and cleaned of query parameters
- Invalid or non-YouTube URLs raise `ValueError`

### Spoofing Prevention

The host check uses exact matching and `.endswith()` rather than substring matching. This prevents attacks like:
- `https://not-youtube.com/watch?v=xxx` (rejected -- not a youtube.com domain)
- `https://youtube.com.evil.com/watch?v=xxx` (rejected -- `evil.com` doesn't end with `.youtube.com`)

### Local Video Validation (`tools/video_file.py`)

Local files are validated for:
- **Existence**: `Path.exists()`
- **File type**: `Path.is_file()`
- **Extension**: Must be in `SUPPORTED_VIDEO_EXTENSIONS` (mp4, webm, mov, avi, mkv, mpeg, wmv, 3gpp)

Files under 20 MB use inline `Part.from_bytes()`. Larger files are uploaded via the Gemini File API with polling until ACTIVE state.

---

## 12. Error Handling

### ToolError Model (`errors.py`)

All tool errors return a consistent Pydantic model:

```python
class ToolError(BaseModel):
    error: str                        # Exception message
    category: str                     # ErrorCategory enum value
    hint: str                         # Human-readable recovery hint
    retryable: bool = False           # Whether the caller should retry
    retry_after_seconds: int | None   # Suggested wait (quota errors only)
```

### Error Categories

| Category | Trigger Pattern | Retryable |
|----------|----------------|-----------|
| `URL_INVALID` | URL parsing failures | No |
| `URL_PARSE_FAILED` | URL extraction failures | No |
| `API_PERMISSION_DENIED` | 403 + "permission" | No |
| `API_QUOTA_EXCEEDED` | 429, "quota", "resource_exhausted" | Yes (60s) |
| `API_INVALID_ARGUMENT` | 400 errors, invalid params | No |
| `API_NOT_FOUND` | 404 errors | No |
| `VIDEO_RESTRICTED` | 403 (non-permission) | No |
| `VIDEO_PRIVATE` | "private" in message | No |
| `VIDEO_UNAVAILABLE` | "unavailable" in message | No |
| `NETWORK_ERROR` | "timeout", "timed out" | Yes |
| `FILE_NOT_FOUND` | `FileNotFoundError` | No |
| `FILE_UNSUPPORTED` | "unsupported video extension" | No |
| `FILE_TOO_LARGE` | -- | No |
| `WEAVIATE_CONNECTION` | "weaviate" + connect patterns | Yes |
| `WEAVIATE_SCHEMA` | "weaviate" + schema patterns | No |
| `WEAVIATE_QUERY` | "weaviate" (generic) | No |
| `WEAVIATE_IMPORT` | "weaviate" + import patterns | No |
| `UNKNOWN` | Everything else | No |

### Categorization

`categorize_error(exc)` maps exceptions to `(ErrorCategory, hint)` by pattern-matching the exception message string. It checks patterns in priority order (most specific first).

### Tool Integration

```python
def make_tool_error(error: Exception) -> dict:
    cat, hint = categorize_error(error)
    retryable = cat in {API_QUOTA_EXCEEDED, NETWORK_ERROR, WEAVIATE_CONNECTION}
    return ToolError(
        error=str(error),
        category=cat.value,
        hint=hint,
        retryable=retryable,
        retry_after_seconds=60 if cat == API_QUOTA_EXCEEDED else None,
    ).model_dump()
```

Convention: Tools **never raise**. Every exception path returns `make_tool_error(exc)`.

---

## 13. Prompt Templates

### Research Prompts (`prompts/research.py`)

**System prompt** (`DEEP_RESEARCH_SYSTEM`): Sets the non-sycophantic analyst persona. Requires evidence-tier labeling on all claims.

**Phase templates** (all use `.format()` interpolation):

| Template | Variables | Purpose |
|----------|-----------|---------|
| `SCOPE_DEFINITION` | `{topic}`, `{scope}` | Define research scope, stakeholders, constraints |
| `EVIDENCE_COLLECTION` | `{topic}`, `{context}` | Extract findings with evidence tiers |
| `SYNTHESIS` | `{topic}`, `{findings_text}` | Synthesize findings into executive summary |
| `RESEARCH_PLAN` | `{topic}`, `{scope}`, `{available_agents}` | Generate phased execution plan |
| `EVIDENCE_ASSESSMENT` | `{claim}`, `{sources_text}`, `{context}` | Assess claim against sources |

### Content Prompts (`prompts/content.py`)

**`STRUCTURED_EXTRACT`**: Template for `content_extract` tool. Interpolates `{content}` and `{schema_description}` to produce a JSON extraction prompt.

### Video Prompts

The video analysis preamble lives in `tools/video_core.py` (not in `prompts/`):

```python
_ANALYSIS_PREAMBLE = (
    "Analyze this video thoroughly. For timestamps, use PRECISE times from the "
    "actual video (not rounded estimates). Extract AT LEAST 5-10 key points. ..."
)
```

This is prepended to the user's instruction for default-schema video analysis.
