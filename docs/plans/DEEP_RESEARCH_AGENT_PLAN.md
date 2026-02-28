# Deep Research Agent Integration Plan

> **Date:** 2026-02-28
> **Scope:** Add 3 new MCP tools leveraging the Gemini Deep Research Agent (Interactions API)
> **Status:** Planned

---

## 1. Problem Statement

Our current `research_deep` tool runs a 3-phase local pipeline (Scope → Evidence → Synthesis) that takes 10-30 seconds and costs $0.02-0.10 per call. It relies solely on Gemini's training knowledge — **it cannot search the web**. This limits it to topics within the model's training data and produces results without citations or source verification.

Google's new **Gemini Deep Research Agent** (`deep-research-pro-preview-12-2025`) is an autonomous agent that plans, searches the real web (80-160 queries), reads sources, iterates, and produces detailed cited reports. It runs 2-20 minutes and costs $2-5 per task, but delivers analyst-grade output with web-grounded citations.

**Goal:** Expose the Deep Research Agent through our MCP server while keeping the existing `research_deep` tool unchanged. The two serve different use cases:

| Dimension | `research_deep` (keep) | Deep Research Agent (new) |
|-----------|----------------------|--------------------------|
| Speed | 10-30 seconds | 2-20 minutes |
| Cost | $0.02-0.10 | $2-5 |
| Web access | None | Built-in Google Search |
| Output | Structured JSON (Pydantic) | Long-form markdown with citations |
| Use case | Quick structured analysis | Comprehensive grounded research |

---

## 2. API Analysis

### 2.1 Interactions API vs. Generate Content API

The Deep Research Agent uses the **Interactions API** — an entirely different API surface from the `generate_content` API our tools currently use.

| Aspect | Generate Content (current) | Interactions (new) |
|--------|---------------------------|-------------------|
| SDK method | `client.aio.models.generate_content()` | `client.interactions.create()` / `.get()` |
| Execution | Synchronous (returns when done) | Asynchronous (background, poll for results) |
| State | Stateless (per-request) | Stateful (interaction ID persists server-side) |
| Response | `GenerateContentResponse` with parts | `Interaction` with outputs, status |
| Follow-ups | Not supported (new request each time) | `previous_interaction_id` chains conversations |

### 2.2 SDK Verification

We verified the Interactions API is available in our current environment:

- **Pinned dependency:** `google-genai>=1.0` (in `pyproject.toml`)
- **Installed version:** `google-genai==1.55.0` (in `uv.lock`)
- **API availability:** `client.interactions` exists with 4 methods: `create`, `get`, `delete`, `cancel`
- **Deep Research support:** `DeepResearchAgentConfig` type available
- **Status:** Marked as experimental (emits `UserWarning` on access)
- **Verdict:** No version bump needed. Current SDK fully supports the Interactions API.

### 2.3 Interactions API Methods

```python
# Start a deep research task (async, returns immediately)
interaction = client.interactions.create(
    input="Research the history of Google TPUs.",
    agent="deep-research-pro-preview-12-2025",
    background=True,
    agent_config={"type": "deep-research", "thinking_summaries": "auto"},
)
# Returns: Interaction(id="...", status="in_progress")

# Poll for results
interaction = client.interactions.get(interaction.id)
# Returns: Interaction(status="in_progress"|"completed"|"failed", outputs=[...])

# Get the final report text
report = interaction.outputs[-1].text

# Cancel a running task
client.interactions.cancel(interaction.id)

# Ask follow-up questions (synchronous, uses regular model)
followup = client.interactions.create(
    input="Can you elaborate on section 2?",
    model="gemini-3.1-pro-preview",
    previous_interaction_id=interaction.id,
)
```

### 2.4 Key API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input` | `str` or `list` | Yes | Research prompt (text or multimodal parts) |
| `agent` | `str` | Yes | Must be `"deep-research-pro-preview-12-2025"` |
| `background` | `bool` | Yes | Must be `True` — runs agent asynchronously |
| `stream` | `bool` | No | SSE streaming with reconnection support |
| `tools` | `list` | No | Additional tools (e.g., File Search for user data) |
| `agent_config` | `dict` | No | `{"type": "deep-research", "thinking_summaries": "auto"}` |
| `previous_interaction_id` | `str` | No | Chain follow-up questions to completed research |

### 2.5 API Limitations (Beta)

- **Max research time:** 60 minutes per task
- **No custom tools:** Cannot pass Function Calling or remote MCP servers
- **No structured output:** Returns markdown, not JSON
- **No plan approval:** Cannot review/approve the agent's research plan
- **Audio inputs:** Not supported
- **Store requirement:** `background=True` requires `store=True` (implicit)

---

## 3. Architecture Decision: Start/Poll Pattern

### 3.1 The Problem

MCP tools are request-response: the calling agent sends a tool call and blocks until the response arrives. Deep Research tasks take 2-20 minutes. Blocking an MCP tool call for 20 minutes is impractical — it would timeout, consume excessive context, and prevent the calling agent from doing anything else.

### 3.2 The Solution

**Start/poll pattern** — the same pattern used by `video_create_session` / `video_continue_session`:

```
Agent calls research_agent_start("quantum computing")
  → Returns { interaction_id: "abc123", status: "in_progress" }  (instant)

Agent does other work...

Agent calls research_agent_poll("abc123")
  → Returns { status: "in_progress" }  (instant)

Agent does more work...

Agent calls research_agent_poll("abc123")
  → Returns { status: "completed", report: "# Research Report\n..." }

Agent calls research_agent_followup("abc123", "elaborate on section 2")
  → Returns { response: "Section 2 discusses..." }
```

### 3.3 Why No Local State

Unlike video sessions (which store conversation history locally in `SessionStore`), Deep Research interactions maintain **all state server-side at Google**. The tools just need the `interaction_id` — they call `client.interactions.get(id)` to retrieve status and results. This makes the implementation significantly simpler: no session store, no eviction logic, no SQLite persistence.

### 3.4 Comparison with Video Session Pattern

| Aspect | Video Sessions | Deep Research |
|--------|---------------|---------------|
| State location | Local (`SessionStore` in-memory + SQLite) | Server-side (Google Interactions API) |
| ID generation | Local `uuid4().hex[:12]` | Server-generated `interaction.id` |
| History management | Local (trim to max turns) | Server-managed |
| TTL/eviction | Local (configurable timeout) | Server-managed (60 min max) |
| Persistence | Optional SQLite | Always (Google stores it) |

---

## 4. Design: 3 New Tools

### 4.1 Tool 1: `research_agent_start`

**Purpose:** Start an autonomous deep research task. Returns immediately with an interaction ID.

```python
@deep_research_server.tool(
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True)
)
async def research_agent_start(
    topic: TopicParam,
    format_instructions: Annotated[str, Field(
        description="Output format instructions (e.g., 'technical report with data tables')"
    )] = "",
    thinking_summaries: Annotated[bool, Field(
        description="Include thinking process summaries in streaming"
    )] = True,
) -> dict:
    """Start an autonomous deep research task with web search.

    Uses the Gemini Deep Research Agent — an autonomous multi-step agent that
    plans, searches the web, reads sources, and writes a detailed cited report.
    Takes 2-20 minutes. Costs approximately $2-5 per task.

    Returns an interaction_id immediately. Use research_agent_poll to check
    results. Use research_agent_followup to ask questions about the report.

    Args:
        topic: Research question or subject area.
        format_instructions: Optional output format guidance.
        thinking_summaries: Whether to enable thinking summaries.

    Returns:
        Dict with interaction_id, status ("in_progress"), and topic.
    """
```

**Implementation notes:**
- Combines `topic` + `format_instructions` into a single input string
- Calls `client.interactions.create(input=..., agent=cfg.deep_research_agent, background=True)`
- Returns `DeepResearchStart(interaction_id=interaction.id, status="in_progress", topic=topic).model_dump()`

### 4.2 Tool 2: `research_agent_poll`

**Purpose:** Check the status of a running deep research task. Returns the report when complete.

```python
@deep_research_server.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True)
)
async def research_agent_poll(
    interaction_id: Annotated[str, Field(min_length=1, description="Interaction ID from research_agent_start")],
    cancel: Annotated[bool, Field(description="Cancel the running research task")] = False,
) -> dict:
    """Check status of a deep research task, or cancel it.

    Poll periodically (recommended every 10-30 seconds) until status
    is "completed" or "failed". Completed results include the full
    markdown report with citations.

    Args:
        interaction_id: The ID returned by research_agent_start.
        cancel: If True, cancels the running task instead of polling.

    Returns:
        Dict with interaction_id, status, and report (when completed).
    """
```

**Implementation notes:**
- If `cancel=True`: calls `client.interactions.cancel(interaction_id)`, returns `{"interaction_id": ..., "status": "cancelled"}`
- Otherwise: calls `client.interactions.get(interaction_id)`
- Status mapping: `"in_progress"` → return as-is; `"completed"` → extract `outputs[-1].text`, store to Weaviate; `"failed"` → extract error

### 4.3 Tool 3: `research_agent_followup`

**Purpose:** Ask a follow-up question about a completed research report.

```python
@deep_research_server.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True)
)
async def research_agent_followup(
    interaction_id: Annotated[str, Field(min_length=1, description="Completed interaction ID")],
    question: Annotated[str, Field(min_length=3, description="Follow-up question about the research report")],
) -> dict:
    """Ask a follow-up question about a completed deep research report.

    Chains to the original research context via previous_interaction_id.
    Uses the standard Gemini model (not the research agent) for fast responses.

    Args:
        interaction_id: ID of a completed deep research interaction.
        question: The follow-up question to ask.

    Returns:
        Dict with new interaction_id, the previous ID, and the response text.
    """
```

**Implementation notes:**
- Calls `client.interactions.create(input=question, model=cfg.default_model, previous_interaction_id=interaction_id)` — synchronous (no `background=True`)
- Follow-ups use the regular Gemini model, not the Deep Research Agent
- Returns `DeepResearchFollowup(interaction_id=new.id, previous_interaction_id=interaction_id, response=text).model_dump()`

---

## 5. File-by-File Changes

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/video_research_mcp/models/deep_research.py` | ~40 | 3 Pydantic output models |
| `src/video_research_mcp/tools/deep_research.py` | ~180 | Sub-server with 3 tools |
| `tests/test_deep_research_tools.py` | ~200 | Unit tests with mocked Interactions API |

### Modified Files

| File | Change | Lines Added |
|------|--------|-------------|
| `src/video_research_mcp/server.py` | Import + mount `deep_research_server` | ~2 |
| `src/video_research_mcp/config.py` | Add `deep_research_agent` config field | ~3 |
| `src/video_research_mcp/errors.py` | Add `INTERACTIONS_API_UNAVAILABLE` category | ~2 |
| `src/video_research_mcp/weaviate_store.py` | Add `store_deep_research()` function | ~30 |

### Unchanged Files

- `tools/research.py` — existing 3 tools untouched (different use case)
- `models/research.py` — existing models untouched
- `client.py` — reuse `GeminiClient.get()` to obtain `genai.Client`; call `client.interactions.*` directly
- `weaviate_schema.py` — reuse existing `ResearchFindings` collection
- `types.py` — no new type aliases needed

---

## 6. Weaviate Storage Strategy

### Reuse `ResearchFindings` Collection

Rather than creating a new collection (which would require schema changes and knowledge tool updates), we store deep research reports in the existing `ResearchFindings` collection with a distinguishing `source_tool` value:

```python
async def store_deep_research(report_text: str, topic: str) -> str | None:
    """Persist a deep research agent report to ResearchFindings."""
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("ResearchFindings")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "research_agent",
                "topic": topic,
                "executive_summary": report_text[:500],
                "reasoning": report_text,
                "evidence_tier": "DEEP_RESEARCH_AGENT",
                "confidence": 1.0,
            }))
        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
```

**Why reuse:** The existing `knowledge_search` tool already queries `ResearchFindings`. By storing deep research reports here with `source_tool: "research_agent"`, they become immediately discoverable via the existing knowledge tools without any changes. Users can distinguish them by the `evidence_tier: "DEEP_RESEARCH_AGENT"` marker.

---

## 7. Configuration

### New Config Field

```python
# config.py — ServerConfig
deep_research_agent: str = Field(default="deep-research-pro-preview-12-2025")

# from_env()
deep_research_agent=os.getenv("GEMINI_DEEP_RESEARCH_AGENT", "deep-research-pro-preview-12-2025"),
```

### New Environment Variable

| Variable | Default | Notes |
|----------|---------|-------|
| `GEMINI_DEEP_RESEARCH_AGENT` | `deep-research-pro-preview-12-2025` | Agent model ID (may change as Google releases new versions) |

**Note:** The Deep Research Agent model is **fixed** — it does not respect the `GEMINI_MODEL` setting or model presets (best/stable/budget). This is because Google provides a single agent endpoint. The config field exists so users can update to newer agent versions without code changes.

---

## 8. Error Handling

### Graceful Degradation

The Interactions API is marked as "experimental" in the SDK. The tools must handle:

1. **SDK too old:** `client.interactions` may not exist. Return a clear error: `"Deep Research Agent requires google-genai >= 1.50. Current version: X.Y.Z"`
2. **API errors:** Rate limits, quota, authentication — handled via `make_tool_error()`
3. **Beta instability:** Unexpected response shapes — defensive parsing with fallback to raw error
4. **Experimental warning:** Suppress the `UserWarning` emitted when accessing `client.interactions`

```python
import warnings

try:
    client = GeminiClient.get()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        interaction = client.interactions.create(...)
except AttributeError:
    return {
        "error": "Interactions API not available in installed google-genai version",
        "category": "INTERACTIONS_API_UNAVAILABLE",
        "hint": "Upgrade: pip install 'google-genai>=1.50'",
        "retryable": False,
    }
except Exception as exc:
    return make_tool_error(exc)
```

---

## 9. Testing Strategy

### Mock Approach

Mock `GeminiClient.get()` to return a mock client with `.interactions.create()` and `.interactions.get()` methods. This mirrors the existing `mock_gemini_client` fixture pattern.

```python
@pytest.fixture()
def mock_interactions_client():
    """Mock the Interactions API on the Gemini client."""
    with patch("video_research_mcp.client.GeminiClient.get") as mock_get:
        mock_client = MagicMock()
        mock_interactions = MagicMock()
        mock_client.interactions = mock_interactions
        mock_get.return_value = mock_client
        yield {
            "client": mock_client,
            "create": mock_interactions.create,
            "get": mock_interactions.get,
            "cancel": mock_interactions.cancel,
        }
```

### Test Cases (~10 tests)

| Test | Scenario |
|------|----------|
| `test_start_returns_interaction_id` | Happy path: create returns interaction with ID |
| `test_start_with_format_instructions` | Format instructions appended to input |
| `test_start_api_error` | API failure returns `make_tool_error()` |
| `test_start_sdk_missing_interactions` | Old SDK returns clear error |
| `test_poll_in_progress` | Returns `{"status": "in_progress"}` |
| `test_poll_completed` | Returns report text, Weaviate store called |
| `test_poll_failed` | Returns error_message |
| `test_poll_cancel` | Calls `cancel()`, returns `{"status": "cancelled"}` |
| `test_followup_success` | Passes `previous_interaction_id`, returns response |
| `test_followup_error` | Invalid interaction ID returns error |

---

## 10. Implementation Order

```
Step 1: models/deep_research.py          (output models, no deps)
Step 2: config.py                         (add deep_research_agent field)
Step 3: errors.py                         (add INTERACTIONS_API_UNAVAILABLE)
Step 4: tools/deep_research.py            (3 tools, depends on steps 1-3)
Step 5: weaviate_store.py                 (add store_deep_research)
Step 6: server.py                         (mount deep_research_server)
Step 7: tests/test_deep_research_tools.py (full test suite)
Step 8: verify                            (pytest + ruff + server startup)
```

---

## 11. Verification Checklist

- [ ] `uv run pytest tests/test_deep_research_tools.py -v` — all new tests pass
- [ ] `uv run pytest tests/ -v` — all 303+ tests pass (no regressions)
- [ ] `uv run ruff check src/ tests/` — lint clean
- [ ] `GEMINI_API_KEY=test uv run video-research-mcp` — server starts without import errors
- [ ] 3 new tools visible in MCP tool inventory: `research_agent_start`, `research_agent_poll`, `research_agent_followup`
- [ ] Existing `research_deep`, `research_plan`, `research_assess_evidence` tools unaffected

---

## 12. Future Enhancements (Out of Scope)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| Streaming support | Use `stream=True` + SSE for real-time progress updates | Medium |
| Multimodal inputs | Accept images/PDFs as research context | Low |
| File Search integration | Allow querying user's uploaded file stores | Low |
| New Weaviate collection | Dedicated `DeepResearchReports` collection for long-form reports | Low |
| Plugin assets | `/gr:deep-research` command + skill documentation | Medium |
| Cost guard | `cost_acknowledged: bool` parameter to prevent accidental expensive calls | Medium |

---

## 13. Key Patterns to Reuse (Reference)

| Pattern | File:Lines | Usage |
|---------|-----------|-------|
| `GeminiClient.get()` → `genai.Client` | `client.py:38-46` | Get client for `.interactions.*` |
| `make_tool_error(exc)` | `errors.py:108-121` | All exception handling |
| Non-fatal Weaviate store | `weaviate_store.py:352-389` | `store_deep_research()` template |
| `ToolAnnotations` decorator | `tools/video.py:117-122` | Tool registration |
| `Annotated[str, Field(...)]` params | `tools/research.py:37-41` | Parameter definitions |
| Pydantic `.model_dump()` return | `tools/video.py:185-188` | Tool return values |
| Config `from_env()` env var | `config.py:83-107` | New config field |
| `TopicParam` type alias | `types.py:23` | `topic` parameter reuse |
