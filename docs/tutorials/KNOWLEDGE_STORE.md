# Knowledge Store

How the knowledge store works, how to set up Weaviate, and how to use the 8 knowledge tools for persistent semantic search across all tool results.

## What It Is

The knowledge store is an **optional Weaviate-backed persistence layer** that automatically saves results from every tool call. When enabled, each tool's output is written through to a Weaviate collection, building a searchable knowledge base over time.

Without Weaviate configured, the server works identically -- knowledge tools return empty results and write-through calls are silently skipped.

## Architecture

```
Tool call (e.g., video_analyze)
  |
  +-- Returns result to caller (always)
  |
  +-- Writes to Weaviate collection (if enabled, non-blocking, non-fatal)
       |
       +-- VideoAnalyses collection

Knowledge tools (knowledge_search, knowledge_related, knowledge_ask, etc.)
  |
  +-- Query Weaviate collections
  |
  +-- Return ranked results to caller
```

Three modules implement the knowledge store:

| Module | Responsibility |
|--------|---------------|
| `weaviate_client.py` | Singleton client, connection management, schema bootstrap |
| `weaviate_schema.py` | 7 collection definitions (PropertyDef, CollectionDef dataclasses) |
| `weaviate_store.py` | Write-through functions (one per collection) |

The 8 knowledge tools live in `tools/knowledge/` (split into `search.py`, `retrieval.py`, `ingest.py`, and `query_agent.py`).

## Setup

### Option A: Local Weaviate (Docker)

```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -p 50051:50051 \
  cr.weaviate.io/semitechnologies/weaviate:latest \
  --host 0.0.0.0 \
  --port 8080 \
  --scheme http
```

Set the env var:

```bash
export WEAVIATE_URL="http://localhost:8080"
```

### Option B: Weaviate Cloud (WCS)

Create a cluster at [console.weaviate.cloud](https://console.weaviate.cloud), then:

```bash
export WEAVIATE_URL="https://your-cluster.weaviate.network"
export WEAVIATE_API_KEY="your-weaviate-api-key"
```

### Verify Connection

Start the MCP server. On first connection, it will auto-create all 7 collections if they do not exist. Check logs for:

```
INFO: Connected to Weaviate at http://localhost:8080
INFO: Created Weaviate collection: ResearchFindings
INFO: Created Weaviate collection: VideoAnalyses
...
```

## The 7 Collections

Each collection stores results from specific tools. All collections share two common properties: `created_at` (date) and `source_tool` (text).

### ResearchFindings

Stores findings from `research_deep` and `research_assess_evidence`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| topic | text | yes | Research topic |
| scope | text | no | Research scope |
| claim | text | yes | Individual finding or claim |
| evidence_tier | text | no | CONFIRMED, STRONG INDICATOR, INFERENCE, SPECULATION, UNKNOWN |
| reasoning | text | yes | Supporting reasoning |
| executive_summary | text | yes | Report executive summary |
| confidence | number | no | Confidence score 0-1 |
| open_questions | text[] | no | Open research questions |

### VideoAnalyses

Stores results from `video_analyze` and `video_batch_analyze`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| video_id | text | no | YouTube video ID or file hash |
| source_url | text | no | Source URL or file path |
| instruction | text | yes | Analysis instruction used |
| title | text | yes | Video title |
| summary | text | yes | Analysis summary |
| key_points | text[] | yes | Key points extracted |
| raw_result | text | no | Full JSON result |

### ContentAnalyses

Stores results from `content_analyze`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| source | text | no | Source URL, file path, or '(text)' |
| instruction | text | yes | Analysis instruction used |
| title | text | yes | Content title |
| summary | text | yes | Analysis summary |
| key_points | text[] | yes | Key points extracted |
| entities | text[] | yes | Named entities found |
| raw_result | text | no | Full JSON result |

### VideoMetadata

Stores YouTube metadata from `video_metadata`. Uses deterministic UUIDs based on `video_id` for automatic deduplication.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| video_id | text | no | YouTube video ID |
| title | text | yes | Video title |
| description | text | yes | Video description |
| channel_title | text | yes | Channel name |
| tags | text[] | yes | Video tags |
| view_count | int | no | View count |
| like_count | int | no | Like count |
| duration | text | no | Video duration |
| published_at | text | no | Publish date |

### SessionTranscripts

Stores conversation turns from `video_continue_session`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| session_id | text | no | Session ID |
| video_title | text | yes | Video title for this session |
| turn_index | int | no | Turn number in session |
| turn_prompt | text | yes | User prompt for this turn |
| turn_response | text | yes | Model response for this turn |

### WebSearchResults

Stores results from `web_search`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| query | text | yes | Search query |
| response | text | yes | Search response text |
| sources_json | text | no | Grounding sources as JSON |

### ResearchPlans

Stores orchestration plans from `research_plan`.

| Property | Type | Vectorized | Description |
|----------|------|-----------|-------------|
| topic | text | yes | Research topic |
| scope | text | no | Research scope |
| task_decomposition | text[] | yes | Task breakdown |
| phases_json | text | no | Phases as JSON |

## Using the Knowledge Tools

### knowledge_search -- search across collections

Supports three search modes: hybrid (default), semantic, and keyword.

```
Use knowledge_search with query "transformer architecture"
Use knowledge_search with query "RLHF" and search_type "semantic"
Use knowledge_search with query "batch normalization" and search_type "keyword"
```

Parameters:
- `query` (required) -- search text
- `search_type` (optional) -- `"hybrid"` (default), `"semantic"`, or `"keyword"`
- `collections` (optional) -- list of collection names to search; defaults to all 7
- `limit` (optional) -- max results per collection (default 10)
- `alpha` (optional) -- hybrid balance: 0.0 = pure keyword, 1.0 = pure vector, 0.5 = balanced (hybrid mode only)

Search modes:
- **hybrid** -- fuses BM25 keyword scores with vector similarity via `collection.query.hybrid()`
- **semantic** -- pure vector similarity via `collection.query.near_text()`; finds semantically similar content even without keyword overlap
- **keyword** -- pure BM25 keyword matching via `collection.query.bm25()`; precise when you know the exact terms

Results are merged across collections and sorted by score descending.

### knowledge_related -- find similar objects

Uses Weaviate's near-object vector search to find semantically related entries.

```
Use knowledge_related with object_id "uuid-from-search" and collection "VideoAnalyses"
```

Parameters:
- `object_id` (required) -- UUID of the source object (from a search result)
- `collection` (required) -- which collection the source belongs to
- `limit` (optional) -- max results (default 5)

The source object is automatically excluded from results.

### knowledge_stats -- object counts

```
Use knowledge_stats
Use knowledge_stats with collection "ResearchFindings"
```

Returns per-collection counts and total. Useful for monitoring knowledge base growth.

### knowledge_fetch -- retrieve object by UUID

Fetch a single object directly by its UUID. Useful for retrieving specific objects found in search results.

```
Use knowledge_fetch with object_id "uuid-from-search" and collection "ResearchFindings"
```

Parameters:
- `object_id` (required) -- Weaviate UUID of the object
- `collection` (required) -- which collection the object belongs to

Returns `found: true` with the object's properties, or `found: false` if the UUID doesn't exist.

### knowledge_ingest -- manual data entry

Insert data directly into any collection. Properties are validated against the collection schema.

```
Use knowledge_ingest with collection "ResearchFindings" and properties:
{"topic": "AI Safety", "claim": "RLHF reduces harmful outputs", "evidence_tier": "CONFIRMED", "confidence": 0.85}
```

Unknown properties are rejected with an error listing the allowed fields.

### knowledge_ask -- AI-generated answers (QueryAgent)

Ask a natural-language question and get a synthesized answer with source citations. Powered by Weaviate's QueryAgent.

```
Use knowledge_ask with query "What were the key findings about transformer architectures?"
Use knowledge_ask with query "How does RLHF work?" and collections ["ResearchFindings"]
```

Parameters:
- `query` (required) -- natural-language question
- `collections` (optional) -- list of collection names to query; defaults to all 7

Returns an AI-generated `answer` string plus a `sources` list with collection name and object UUID for each cited source.

**Requires**: `pip install video-research-mcp[agents]` (installs `weaviate-agents>=1.2.0`). Returns a clear error hint if the package is not installed.

### knowledge_query -- natural language object retrieval (QueryAgent)

Retrieve objects using a natural-language query. Unlike `knowledge_search` (where you choose the search mode), QueryAgent automatically translates your query into optimized Weaviate operations.

```
Use knowledge_query with query "videos about machine learning published this week"
Use knowledge_query with query "research findings with high confidence about LLMs" and limit 5
```

Parameters:
- `query` (required) -- natural-language search description
- `collections` (optional) -- list of collection names to search; defaults to all 7
- `limit` (optional) -- max results (default 10)

Returns matched objects with collection, UUID, score, and properties -- the same `KnowledgeHit` format as `knowledge_search`.

**Requires**: `pip install video-research-mcp[agents]` (installs `weaviate-agents>=1.2.0`).

### How QueryAgent differs from knowledge_search

| Feature | `knowledge_search` | `knowledge_ask` / `knowledge_query` |
|---------|--------------------|------------------------------------|
| Search mode | Explicit (hybrid/semantic/keyword) | Automatic (QueryAgent decides) |
| Filters | Manual (evidence_tier, date_from, etc.) | Inferred from natural language |
| Output | Raw objects with scores | `ask`: synthesized answer + sources; `query`: objects |
| Dependency | `weaviate-client` only | `weaviate-agents` (optional) |
| Best for | Precise, repeatable queries | Exploratory questions, complex multi-collection queries |

The QueryAgent instance is lazily created on first use and cached by the frozenset of target collection names. If the collection set changes between calls, a new agent is created.

## Write-Through Store Pattern

Every tool that produces results automatically writes them to Weaviate via functions in `weaviate_store.py`. This is the biggest architectural pattern to understand when adding new tools.

### Which tools store to which collections

| Tool | Store function | Collection |
|------|---------------|------------|
| `video_analyze` | `store_video_analysis` | VideoAnalyses |
| `video_batch_analyze` | `store_video_analysis` (per file) | VideoAnalyses |
| `video_continue_session` | `store_session_turn` | SessionTranscripts |
| `video_metadata` | `store_video_metadata` | VideoMetadata |
| `content_analyze` | `store_content_analysis` | ContentAnalyses |
| `research_deep` | `store_research_finding` | ResearchFindings |
| `research_plan` | `store_research_plan` | ResearchPlans |
| `research_assess_evidence` | `store_evidence_assessment` | ResearchFindings |
| `web_search` | `store_web_search` | WebSearchResults |

### The pattern

```python
# In a tool function, after computing the result:
from ..weaviate_store import store_video_analysis
await store_video_analysis(result, content_id, instruction, source_url)
```

Each store function follows the same structure:

```python
async def store_video_analysis(result, content_id, instruction, source_url=""):
    """Store a video analysis result. Returns UUID or None."""
    if not _is_enabled():          # Guard: skip if Weaviate not configured
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoAnalyses")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "video_analyze",
                "video_id": content_id,
                "source_url": source_url,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "raw_result": json.dumps(result),
            }))
        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None                # Never fail the tool call
```

Key design decisions:

1. **Non-fatal** -- store failures are logged as warnings, never propagated to the caller
2. **Non-blocking** -- runs in a thread via `asyncio.to_thread` since the Weaviate client is synchronous
3. **Guard check** -- `_is_enabled()` returns False if `WEAVIATE_URL` is not set
4. **Timestamp** -- `_now()` returns UTC datetime (Weaviate accepts datetime objects directly)

### Adding a store function for a new tool

1. Add the function to `weaviate_store.py`
2. Map result fields to collection properties
3. Call it from your tool after computing the result

If your tool needs a new collection, define it in `weaviate_schema.py` (see next section).

## Adding a New Collection

1. Define the collection in `weaviate_schema.py`:

```python
MY_DATA = CollectionDef(
    name="MyData",
    description="Results from my_tool",
    properties=_common_properties() + [
        PropertyDef("field_a", ["text"], "Description of field A"),
        PropertyDef("field_b", ["int"], "Description of field B",
                    skip_vectorization=True, index_range_filters=True),
        PropertyDef("raw_json", ["text"], "JSON blob",
                    skip_vectorization=True, index_searchable=False),
    ],
)
```

2. Add it to the `ALL_COLLECTIONS` list:

```python
ALL_COLLECTIONS: list[CollectionDef] = [
    # ... existing collections
    MY_DATA,
]
```

3. Add the collection name to `KnowledgeCollection` in `types.py`:

```python
KnowledgeCollection = Literal[
    "ResearchFindings", "VideoAnalyses", "ContentAnalyses",
    "VideoMetadata", "SessionTranscripts", "WebSearchResults", "ResearchPlans",
    "MyData",  # new
]
```

4. Write a store function in `weaviate_store.py` (see pattern above).

5. The collection is created automatically on first server start (idempotent).

### Property configuration

- `data_type` -- Weaviate types: `["text"]`, `["text[]"]`, `["int"]`, `["number"]`, `["date"]`, `["boolean"]`
- `skip_vectorization=True` -- exclude from vector embedding (use for IDs, counts, JSON blobs)
- `index_range_filters=True` -- enable B-tree index for range queries (`>`, `<`, `between`) on int/number/date fields
- `index_searchable=False` -- disable BM25 keyword index on non-searchable text (JSON blobs, IDs, metadata)
- `index_filterable=True` (default) -- roaring-bitmap index for equality/contains filters

Guidelines:
- Properties that carry semantic meaning (titles, summaries, claims) should be vectorized (default) and BM25-searchable (default)
- Properties that are structural (UUIDs, timestamps, raw JSON) should skip vectorization and disable BM25
- Numeric/date fields used in range filters should set `index_range_filters=True`

## Weaviate Client Singleton

`WeaviateClient` in `weaviate_client.py` mirrors the `GeminiClient` pattern:

- **`get()`** -- returns (or creates) the shared client; thread-safe
- **`ensure_collections()`** -- idempotent schema creation on first connect
- **`is_available()`** -- checks if configured and reachable
- **`close()` / `aclose()`** -- cleanup (called in server lifespan shutdown)

Connection is automatic based on URL scheme:
- `http://localhost:*` -- connects via `weaviate.connect_to_local`
- `https://*.weaviate.network` -- connects via `weaviate.connect_to_weaviate_cloud`
- Other URLs -- connects via `weaviate.connect_to_custom`

All connections include `Timeout(init=30, query=60, insert=120)` for production reliability.

## Reference

- [Getting Started](./GETTING_STARTED.md) -- env var setup
- [Adding a New Tool](./ADDING_A_TOOL.md) -- integrating write-through in new tools
- [Writing Tests](./WRITING_TESTS.md) -- `mock_weaviate_client` fixture
- [Architecture Guide](../ARCHITECTURE.md) -- overall server design
- Source: `src/video_research_mcp/weaviate_schema.py` -- collection definitions
- Source: `src/video_research_mcp/weaviate_store.py` -- write-through functions
- Source: `src/video_research_mcp/weaviate_client.py` -- client singleton
- Source: `src/video_research_mcp/tools/knowledge/` -- query tools (8 tools across 4 modules)
