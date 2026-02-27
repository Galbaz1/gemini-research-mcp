# Documentation Audit Report

**Date**: 2026-02-27
**Auditor**: code-reviewer (Claude Opus 4.6)
**Scope**: Full codebase vs CLAUDE.md claims, docstring coverage, undocumented patterns

---

## 1. CLAUDE.md Accuracy vs Code

### 1.1 Tool Count

| Location | Claim | Actual |
|----------|-------|--------|
| "What This Is" (line 7) | "exposing 17 tools" | **17 tools** -- CORRECT |
| Tool Surface table (line 75) | 17 rows | **17 rows** -- CORRECT |
| Tool annotations note (line 65) | "All 11 tools carry ToolAnnotations" | **Should say 17** -- STALE |

**GAP**: Line 65 still references "11 tools" from before the knowledge tools were added. Should read "All 17 tools carry `ToolAnnotations`".

### 1.2 Sub-Server Count

| Location | Claim | Actual |
|----------|-------|--------|
| Line 34 | "mounts 7 sub-servers" | **7 mounts in server.py** -- CORRECT |
| Architecture tree | 7 sub-servers listed | CORRECT (video, youtube, research, content, search, infra, knowledge) |

### 1.3 Architecture Tree

The architecture tree (lines 37-51) is **accurate** against the actual file structure. All listed files exist and serve the described purposes. The following files exist in the codebase but are **not listed** in the tree:

| Missing from tree | Purpose |
|---|---|
| `tools/video_file.py` | Local video file helpers (MIME, hashing, File API upload) |
| `persistence.py` | SQLite-backed session persistence (WAL mode) |
| `retry.py` | Exponential backoff for transient Gemini API errors |

These are important modules that callers need to understand. `persistence.py` and `retry.py` are architectural -- they implement patterns described elsewhere in CLAUDE.md but have no tree entry.

### 1.4 Env Vars Table

| Variable | Documented Default | Actual Default (config.py) | Status |
|----------|-------------------|---------------------------|--------|
| `GEMINI_API_KEY` | (required) | `""` | CORRECT |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` | CORRECT |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | `gemini-3-flash-preview` | CORRECT |
| `GEMINI_THINKING_LEVEL` | `high` | `high` | CORRECT |
| `GEMINI_TEMPERATURE` | `1.0` | `1.0` | CORRECT |
| `GEMINI_CACHE_DIR` | `~/.cache/video-research-mcp/` | `~/.cache/video-research-mcp/` | CORRECT |
| `GEMINI_CACHE_TTL_DAYS` | `30` | `30` | CORRECT |
| `GEMINI_MAX_SESSIONS` | `50` | `50` | CORRECT |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `2` | `2` | CORRECT |
| `GEMINI_SESSION_MAX_TURNS` | `24` | `24` | CORRECT |
| `GEMINI_RETRY_MAX_ATTEMPTS` | `3` | `3` | CORRECT |
| `GEMINI_RETRY_BASE_DELAY` | `1.0` | `1.0` | CORRECT |
| `GEMINI_RETRY_MAX_DELAY` | `60.0` | `60.0` | CORRECT |
| `YOUTUBE_API_KEY` | `""` (falls back to GEMINI_API_KEY) | `""` | CORRECT |
| `GEMINI_SESSION_DB` | `""` (empty = in-memory only) | `""` | CORRECT |
| `WEAVIATE_URL` | `""` (empty = knowledge store disabled) | `""` | CORRECT |
| `WEAVIATE_API_KEY` | `""` (required for Weaviate Cloud) | `""` | CORRECT |

All 17 env vars match. No undocumented config fields exist.

### 1.5 Key Singletons

CLAUDE.md documents 4 singletons. Actual status:

| Singleton | Documented | Actually exists | Notes |
|-----------|-----------|----------------|-------|
| `GeminiClient` (client.py) | Yes | Yes | Accurate description |
| `get_config()` (config.py) | Yes | Yes | Accurate description |
| `session_store` (sessions.py) | Yes | Yes | Description says "in-memory" but sessions.py also supports SQLite persistence via `persistence.py` -- **partially stale** |
| `cache` module (cache.py) | Yes | Yes | Accurate description |
| `WeaviateClient` (weaviate_client.py) | In tree only | Yes | **Missing from singletons list** -- should be documented as a key singleton |

**GAP**: `WeaviateClient` appears in the tree but is not listed under "Key singletons". It follows the same singleton pattern as `GeminiClient` (process-wide, thread-safe, lazy-init).

**GAP**: `session_store` description says "in-memory SessionStore" but the actual implementation supports optional SQLite persistence via `SessionDB` (persistence.py). The description should mention this.

### 1.6 Test Count

| Documented | Actual |
|-----------|--------|
| "72 tests" (line 148) | **228 test functions** across 17 test files |

**GAP**: Massively stale. Test count has grown from 72 to 228. The test files for knowledge/weaviate modules are new additions not reflected in the count.

### 1.7 FastMCP Version

| Documented | pyproject.toml |
|-----------|---------------|
| "FastMCP 3.0.2" (line 7) | `fastmcp>=2.0` |

**MISMATCH**: CLAUDE.md says "FastMCP 3.0.2" but pyproject.toml requires `fastmcp>=2.0`. The version claim should reference the minimum version from pyproject.toml or be removed to avoid staleness.

---

## 2. Tool Docstring Audit

All 17 tools were checked for:
- Docstring presence
- Args section
- Returns section
- ToolAnnotations decorator
- Annotated params with Field

### 2.1 Tool Compliance Matrix

| Tool | Docstring | Args | Returns | ToolAnnotations | Annotated Params |
|------|:---------:|:----:|:-------:|:---------------:|:----------------:|
| `video_analyze` | PASS | PASS | PASS | PASS | PASS |
| `video_create_session` | PASS | PASS | PASS | PASS | PASS |
| `video_continue_session` | PASS | PASS | PASS | PASS | PASS |
| `video_batch_analyze` | PASS | PASS | PASS | PASS | PASS |
| `video_metadata` | PASS | PASS | PASS | PASS | PASS |
| `video_playlist` | PASS | PASS | PASS | PASS | PASS |
| `research_deep` | PASS | PASS | PASS | PASS | PASS |
| `research_plan` | PASS | PASS | PASS | PASS | PASS |
| `research_assess_evidence` | PASS | PASS | PASS | PASS | PASS |
| `content_analyze` | PASS | PASS | PASS | PASS | PASS |
| `content_extract` | PASS | PASS | PASS | PASS | PASS |
| `web_search` | PASS | PASS | PASS | PASS | PASS |
| `infra_cache` | PASS | PASS | PASS | PASS | PASS |
| `infra_configure` | PASS | PASS | PASS | PASS | PASS |
| `knowledge_search` | PASS | PASS | PASS | PASS | PASS |
| `knowledge_related` | PASS | PASS | PASS | PASS | PASS |
| `knowledge_stats` | PASS | PASS | PASS | PASS | PASS |
| `knowledge_ingest` | PASS | PASS | PASS | PASS | PASS |

**Result**: All 17 tools (not 13 as in some CLAUDE.md references) meet the tool conventions. The knowledge tools were added correctly following the established pattern. Note: `knowledge_stats` is listed as 17th -- CLAUDE.md table lists 17 tools including the 4 knowledge tools.

Wait -- recount: video(4) + youtube(2) + research(3) + content(2) + search(1) + infra(2) + knowledge(4) = **18 tools**.

**DISCREPANCY**: The actual tool count is **18**, not 17. CLAUDE.md "What This Is" says 17, and the tool table has 17 rows. The missing tool is `knowledge_ingest` which exists in `tools/knowledge.py` but is listed in the table (line 96). Recounting the table: 14 original + 4 knowledge = 18. Let me recount the table rows:

1. video_analyze
2. video_create_session
3. video_continue_session
4. video_batch_analyze
5. video_metadata
6. video_playlist
7. research_deep
8. research_plan
9. research_assess_evidence
10. content_analyze
11. content_extract
12. web_search
13. infra_cache
14. infra_configure
15. knowledge_search
16. knowledge_related
17. knowledge_stats
18. knowledge_ingest

The CLAUDE.md table actually has **18 rows** but the "What This Is" header says "17 tools" and the "Tool Surface" header says "(17 tools)". **Both should say 18**.

---

## 3. Module Docstring Coverage

Every `.py` file in `src/video_research_mcp/` was checked for a module-level docstring.

| File | Module Docstring | Quality |
|------|:----------------:|---------|
| `__init__.py` | PASS | Brief, adequate |
| `server.py` | PASS | Describes purpose |
| `types.py` | PASS | Describes purpose |
| `config.py` | PASS | Describes purpose |
| `client.py` | PASS | Describes purpose |
| `sessions.py` | PASS | Describes purpose |
| `persistence.py` | PASS | Describes purpose |
| `cache.py` | PASS | Describes purpose |
| `retry.py` | PASS | Describes purpose |
| `errors.py` | PASS | Describes purpose |
| `youtube.py` | PASS | Detailed with context |
| `weaviate_client.py` | PASS | Describes purpose |
| `weaviate_schema.py` | PASS | Describes purpose |
| `weaviate_store.py` | PASS | Describes purpose |
| `tools/__init__.py` | PASS | Brief |
| `tools/video.py` | PASS | Describes purpose + tool count |
| `tools/video_url.py` | PASS | Describes purpose |
| `tools/video_file.py` | PASS | Describes purpose |
| `tools/video_core.py` | PASS | Describes purpose |
| `tools/youtube.py` | PASS | Describes purpose |
| `tools/research.py` | PASS | Describes purpose + tool count |
| `tools/content.py` | PASS | Describes purpose + tool count |
| `tools/search.py` | PASS | Describes purpose |
| `tools/infra.py` | PASS | Describes purpose + tool count |
| `tools/knowledge.py` | PASS | Describes purpose + tool count |
| `models/__init__.py` | PASS | Brief |
| `models/video.py` | PASS | Describes purpose |
| `models/video_batch.py` | PASS | Describes purpose |
| `models/youtube.py` | PASS | Describes purpose |
| `models/research.py` | PASS | Describes purpose |
| `models/content.py` | PASS | Describes purpose |
| `models/knowledge.py` | PASS | Describes purpose |
| `prompts/__init__.py` | PASS | Brief |
| `prompts/research.py` | PASS | Describes purpose |
| `prompts/content.py` | PASS | Describes purpose |

**Result**: 100% module docstring coverage. All 35 source files have module-level docstrings.

---

## 4. Public Function/Class Docstring Coverage

### 4.1 Functions Missing Docstrings

| File | Function | Issue |
|------|----------|-------|
| `tools/video_url.py` | `_is_youtube_host` | No docstring (private, but called externally from `tools/youtube.py`) |
| `tools/video_url.py` | `_is_youtu_be_host` | No docstring |
| `tools/video_url.py` | `_extract_video_id_from_parsed` | No docstring |
| `tools/video_url.py` | `_extract_video_id` | No docstring |
| `tools/video_core.py` | `_enrich_prompt` | No docstring |
| `weaviate_store.py` | `_is_enabled` | Has docstring (private) |
| `weaviate_store.py` | `_now` | Has docstring (private) |
| `weaviate_store.py` | `_meta_properties` | Has docstring (private) |

**Assessment**: Most undocumented functions are private helpers (prefixed `_`). The URL extraction helpers in `video_url.py` are called cross-module, so they are effectively semi-public. `_normalize_youtube_url` and `_video_content` both have docstrings, which is good. The missing ones are simple enough to be self-documenting, but per project conventions, Args/Returns sections would be ideal.

### 4.2 Classes Missing Docstrings

All public classes have docstrings:
- `GeminiClient`, `YouTubeClient`, `WeaviateClient` -- PASS
- `ServerConfig`, `SessionStore`, `VideoSession` -- PASS
- `SessionDB` -- PASS
- All Pydantic models -- PASS
- `ErrorCategory`, `ToolError` -- PASS
- `CollectionDef`, `PropertyDef` -- PASS

---

## 5. Undocumented Patterns in CLAUDE.md

### 5.1 Weaviate Write-Through Pattern

**Code**: Every tool that produces results (`video_analyze`, `content_analyze`, `research_deep`, `research_plan`, `research_assess_evidence`, `video_metadata`, `web_search`, `video_continue_session`) calls a `store_*` function from `weaviate_store.py` after producing results. All store functions are guarded by `_is_enabled()` and wrapped in try/except with non-fatal logging.

**Documentation**: CLAUDE.md does not describe this write-through pattern at all. It documents the knowledge tools and weaviate modules in the architecture tree, but the automatic storage of tool results is nowhere explained. A developer adding a new tool would not know to add a `store_*` call.

**Recommendation**: Add a "Write-through storage" section under Architecture explaining:
- Every tool stores results to Weaviate if enabled
- Store functions are non-fatal (tool succeeds even if store fails)
- Pattern: import store function inside tool, call after result is ready
- Each collection maps to specific tools

### 5.2 Retry Pattern

**Code**: `retry.py` provides `with_retry()` used by `GeminiClient.generate()`, `web_search`, and `video_continue_session`. It implements exponential backoff with jitter for retryable patterns (429, quota, timeout, 503).

**Documentation**: CLAUDE.md mentions retry config vars (`GEMINI_RETRY_*`) but does not describe the retry mechanism itself. The `retry.py` module is not in the architecture tree.

**Recommendation**: Add `retry.py` to the architecture tree with description "exponential backoff for transient Gemini API errors". Add a sentence under Architecture explaining the retry pattern.

### 5.3 SQLite Session Persistence

**Code**: `persistence.py` provides `SessionDB` with WAL mode, used by `SessionStore` when `GEMINI_SESSION_DB` is set.

**Documentation**: `GEMINI_SESSION_DB` env var is documented, but the persistence mechanism is not described in Architecture. The `persistence.py` module is not in the tree.

**Recommendation**: Add `persistence.py` to the architecture tree. Update the `session_store` singleton description to mention optional SQLite persistence.

### 5.4 Large File Upload Pattern

**Code**: `video_file.py` splits file handling: files <20MB are inlined as `Part.from_bytes`, files >=20MB are uploaded via Gemini File API with polling for ACTIVE state.

**Documentation**: Not described in CLAUDE.md. The 20MB threshold and File API polling are implementation details a maintainer should know about.

**Recommendation**: Brief mention in Architecture or a "Notable patterns" section.

### 5.5 Deterministic UUID for VideoMetadata

**Code**: `weaviate_store.py:store_video_metadata` uses `weaviate.util.generate_uuid5(video_id)` for deterministic UUIDs, enabling upsert behavior (replace-or-insert).

**Documentation**: Not mentioned. This is a subtle but important data integrity pattern.

### 5.6 Model Presets

**Code**: `config.py:MODEL_PRESETS` defines 3 presets ("best", "stable", "budget") with model pairs and labels. `infra_configure` tool uses these.

**Documentation**: Presets are implicitly documented via the `infra_configure` tool entry and the `ModelPreset` type, but the actual model-pair mappings and their labels are not shown in CLAUDE.md.

---

## 6. CLAUDE.md Internal Inconsistencies

| Line | Issue | Severity |
|------|-------|----------|
| 7 | "exposing 17 tools" -- actual count is 18 | Medium |
| 7 | "FastMCP 3.0.2" -- pyproject.toml says `fastmcp>=2.0` | Low |
| 65 | "All 11 tools carry ToolAnnotations" -- should be 18 | Medium |
| 75 | "(17 tools)" heading -- should be 18 | Medium |
| 148 | "72 tests" -- actual count is 228 | Medium |

---

## 7. Missing Test Coverage Areas

Based on module review, the following test files exist but were added recently (per git status showing `??`):

- `tests/test_knowledge_tools.py` (14 tests) -- new, untracked
- `tests/test_weaviate_client.py` (8 tests) -- new, untracked
- `tests/test_weaviate_schema.py` (13 tests) -- new, untracked
- `tests/test_weaviate_store.py` (15 tests) -- new, untracked

The following areas have no dedicated tests:

| Area | Explanation |
|------|-------------|
| `server.py` lifespan hook | No test for `_lifespan` shutdown behavior |
| `weaviate_client._connect()` | URL routing logic (local vs WCS vs custom) is tested in test_weaviate_client.py but worth verifying coverage |
| Tool-level Weaviate store calls | No test verifies that `video_analyze` actually calls `store_video_analysis` |

---

## 8. Summary of Findings

### Critical (should fix before docs release)

1. **Tool count mismatch**: CLAUDE.md says 17 tools in 3 places; actual count is 18
2. **Stale "11 tools" reference**: Line 65 says "All 11 tools" -- should be 18
3. **Test count stale**: Says 72, actual is 228

### Important (should address)

4. **Missing architecture tree entries**: `retry.py`, `persistence.py`, `tools/video_file.py`
5. **Undocumented write-through pattern**: The automatic Weaviate storage from all tools is the biggest undocumented architectural pattern
6. **WeaviateClient missing from singletons**: Listed in tree but not in "Key singletons"
7. **Session store description**: Doesn't mention SQLite persistence option

### Minor (nice to have)

8. **FastMCP version**: "3.0.2" vs `>=2.0` in pyproject.toml
9. **URL helper docstrings**: `_extract_video_id`, `_is_youtube_host` etc. lack docstrings
10. **Model preset details**: Not documented in CLAUDE.md
11. **Large file threshold**: 20MB threshold and File API pattern not documented

---

## 9. Recommended CLAUDE.md Fixes

### Patch 1: Tool count
```
Line 7:  "exposing 17 tools" -> "exposing 18 tools"
Line 65: "All 11 tools" -> "All 18 tools"
Line 75: "(17 tools)" -> "(18 tools)"
```

### Patch 2: Test count
```
Line 148: "72 tests" -> "228 tests" (or "~230 tests" to be approximate)
```

### Patch 3: Architecture tree additions
Add after line 47 (`tools/knowledge.py`):
```
├── tools/video_file.py     -> local file helpers (MIME, hash, File API upload)
├── retry.py                -> exponential backoff for Gemini API errors
├── persistence.py          -> SQLite WAL-mode session persistence
```

### Patch 4: Add WeaviateClient to Key singletons
Add:
```
- `WeaviateClient` (`weaviate_client.py`) -- process-wide Weaviate client (single cluster, thread-safe). Lazy-connects on first `.get()`, auto-creates collections from `weaviate_schema.py`. Disabled when `WEAVIATE_URL` is empty.
```

### Patch 5: Add write-through pattern description
New section under Architecture:
```
**Write-through knowledge storage:** When Weaviate is configured (`WEAVIATE_URL`), every tool automatically stores its results via `weaviate_store.py` functions. Store calls are non-fatal -- tools succeed even if Weaviate write fails. Pattern: import `store_*` inside the tool function, call after result is ready. See `weaviate_store.py` for the per-collection store functions.
```

### Patch 6: Update session_store description
```
- `session_store` (`sessions.py`) -- in-memory `SessionStore` with optional SQLite persistence (`persistence.py`, WAL mode). Enabled by `GEMINI_SESSION_DB` env var.
```
