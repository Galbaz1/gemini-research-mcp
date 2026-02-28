# Plan: Bridge Gemini Context Cache Between video_analyze and video_create_session

## Problem

When a user analyzes a video with `video_analyze` and then starts a chat session with `video_create_session` on the same video, the session returns `cache_status: "uncached"`. Gemini re-processes the entire video from scratch, wasting time and API quota.

## Root Cause

Two independent cache systems that don't talk to each other:

| Layer | File | Purpose | Used by |
|-------|------|---------|---------|
| File cache | `cache.py` | Stores analysis JSON results | `video_analyze` only |
| Context cache | `context_cache.py` | Stores video content at Gemini API level | `video_create_session` only |

`video_analyze` never calls `context_cache.get_or_create()`, so the registry is always empty when `video_create_session` checks it. Additionally, the registry is an in-memory dict (`_registry`) that's lost on every server restart.

### Data flow today (broken)

```
video_analyze("youtube.com/watch?v=abc")
  → Gemini processes video → result cached in file cache
  → context_cache._registry stays EMPTY

video_create_session("youtube.com/watch?v=abc")
  → context_cache.lookup() → miss (registry empty)
  → context_cache.get_or_create() → creates NEW Gemini cache from scratch
  → returns cache_status: "uncached" on first call, "cached" only on repeat sessions
```

### Data flow after fix

```
video_analyze("youtube.com/watch?v=abc")
  → Gemini processes video → result cached in file cache
  → fire-and-forget: context_cache.get_or_create() populates registry
  → registry persisted to disk

video_create_session("youtube.com/watch?v=abc")
  → context_cache._load_registry() → loads from disk
  → context_cache.get_or_create() → HIT (validates with Gemini API)
  → returns cache_status: "cached"
```

## Action Items

### 1. Add disk persistence to `context_cache.py`

**File**: `src/video_research_mcp/context_cache.py`

The in-memory `_registry` dict is lost on every server restart. Add a JSON sidecar file so cache names survive across restarts.

**New functions**:

- `_registry_path()` — Returns `Path(get_config().cache_dir) / "context_cache_registry.json"`
- `_save_registry()` — Serialize `_registry` to JSON after each mutation. Keys stored as `"content_id:model"` (JSON doesn't support tuple keys). Best-effort — never raises.
- `_load_registry()` — Deserialize on first access via a `_loaded` flag (lazy init). On corrupted JSON, fall back to empty registry. Best-effort — never raises.

**New module-level state**:

- `_loaded: bool = False` — Lazy init flag, prevents re-reading the file on every call

**New imports**: `json`, `pathlib.Path`

**Call sites**:

| Where | What to call |
|-------|-------------|
| Start of `get_or_create()` (before line 36) | `_load_registry()` |
| Start of `lookup()` (before line 96) | `_load_registry()` |
| After `_registry[key] = cached.name` in `get_or_create()` (line 65) | `_save_registry()` |
| After `_registry.clear()` in `clear()` (line 123) | `_save_registry()` |

**JSON format on disk**:

```json
{
  "GcNu6wrLTJc:gemini-3.1-pro-preview": "cachedContents/abc123",
  "abc123hash:gemini-3.1-pro-preview": "cachedContents/def456"
}
```

**Design decisions**:
- On load, stale entries are NOT validated. Validation already happens in `get_or_create()` via the Gemini API check (line 42). This avoids N API calls on startup.
- `_load_registry()` uses `dict.setdefault()` so it never overwrites entries added by the current process.
- The `_loaded` flag resets implicitly when the module is re-imported (server restart), which is the exact scenario we want to re-read from disk.

---

### 2. Pre-warm context cache from `video_analyze`

**File**: `src/video_research_mcp/tools/video.py`

After `analyze_video()` returns successfully, fire-and-forget a context cache population for YouTube URLs.

**Change**: Capture the return value of `analyze_video()` into a local, add the pre-warm block, then return the result.

**Before** (lines 187-196):
```python
        return await analyze_video(
            contents,
            instruction=instruction,
            content_id=content_id,
            source_label=source_label,
            output_schema=output_schema,
            thinking_level=thinking_level,
            use_cache=use_cache,
            metadata_context=metadata_context,
        )
```

**After**:
```python
        result = await analyze_video(
            contents,
            instruction=instruction,
            content_id=content_id,
            source_label=source_label,
            output_schema=output_schema,
            thinking_level=thinking_level,
            use_cache=use_cache,
            metadata_context=metadata_context,
        )

        # Pre-warm context cache for future session reuse (YouTube only)
        if url and content_id:
            cfg = get_config()
            _warm_parts = [types.Part(file_data=types.FileData(file_uri=clean_url))]
            asyncio.create_task(
                context_cache.get_or_create(content_id, _warm_parts, cfg.default_model)
            )

        return result
```

**New import** (add to top of file):
```python
from .. import context_cache
from google.genai import types
```

Note: `types` is already imported transitively via other modules, but the `video.py` file doesn't import it directly. Check if `types` is available — if not, add the import.

**Why YouTube only**:
- YouTube URLs have a stable `file_uri` (the normalized YouTube URL) that Gemini can resolve
- Local files < 20MB use `Part.from_bytes()` — no URI available for caching
- Local files >= 20MB use File API upload, but the URI isn't accessible from `_video_file_content()`'s return value
- `video_create_session` for local files calls `_video_file_uri()` which handles its own upload — the session flow already works for local files

**Why fire-and-forget**:
- `asyncio.create_task()` doesn't block the analysis response
- If cache creation fails, sessions fall back to creating their own cache (existing behavior in `video_create_session` line 99)
- No regression possible — worst case is the same behavior as today

---

### 3. Add tests

#### 3a. New class in `tests/test_context_cache.py`

Add `TestRegistryPersistence` class:

| Test | What it verifies |
|------|-----------------|
| `test_save_and_load_roundtrip` | Populate registry → save → clear registry + reset `_loaded` → load → entries restored |
| `test_load_missing_file` | Load with no file on disk → empty registry, no error |
| `test_load_corrupted_file` | Write invalid JSON to path → load → falls back to empty registry, no crash |

**Key fixture need**: Mock `get_config()` to return a config with `cache_dir` pointing to `tmp_path`. The existing `_clean_config` fixture resets config but uses real env vars — the new tests need to override `cache_dir` specifically.

#### 3b. New file `tests/test_cache_bridge.py`

Integration tests for the analyze→session cache reuse flow:

| Test | What it verifies |
|------|-----------------|
| `test_video_analyze_populates_context_cache` | Mock `analyze_video` → verify `context_cache.get_or_create` was called with `(content_id, [video_part], model)` |
| `test_analyze_then_session_gets_cached_status` | Populate registry via direct `context_cache._registry` insertion → call mocked `video_create_session` flow → assert `cache_status == "cached"` |

**Mocking strategy**: Both tests should mock `GeminiClient.get()` and `analyze_video` to avoid real API calls. The bridge test verifies that the *wiring* is correct, not the Gemini API behavior.

---

## Files to Modify

| File | Change type | Description |
|------|------------|-------------|
| `src/video_research_mcp/context_cache.py` | Edit | Add `_loaded`, `_registry_path()`, `_save_registry()`, `_load_registry()`, wire into existing functions |
| `src/video_research_mcp/tools/video.py` | Edit | Add `context_cache` import + pre-warm block after `analyze_video()` |
| `tests/test_context_cache.py` | Edit | Add `TestRegistryPersistence` class (3 tests) |
| `tests/test_cache_bridge.py` | New | Integration tests for analyze→session cache bridge (2 tests) |

## Verification

### Automated

```bash
pytest tests/test_context_cache.py tests/test_cache_bridge.py -v
```

### Manual end-to-end

1. Run `video_analyze(url="https://www.youtube.com/watch?v=GcNu6wrLTJc")`
2. Check `~/.cache/video-research-mcp/context_cache_registry.json` exists with entry
3. Run `video_create_session(url="https://www.youtube.com/watch?v=GcNu6wrLTJc")`
4. Verify response has `cache_status: "cached"` (not `"uncached"`)

### Restart resilience

1. Restart the MCP server
2. Run `video_create_session` for the same URL
3. Should still report `cache_status: "cached"` (if Gemini cache hasn't expired its TTL)

### Graceful degradation

- If Gemini cache has expired, `get_or_create()` recreates it transparently — existing behavior preserved
- If JSON sidecar is missing or corrupted, registry starts empty — same as today
- If `asyncio.create_task()` fails in pre-warm, analysis result is unaffected

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| JSON write fails (disk full, permissions) | Low | `_save_registry()` catches all exceptions, logs debug |
| Corrupted JSON on disk | Low | `_load_registry()` catches parse errors, starts fresh |
| Colon in content_id breaks key parsing | None | `split(":", 1)` handles any colons after the first |
| Pre-warm task exception unhandled | Low | `get_or_create()` already catches all exceptions internally |
| Race between concurrent saves | Very low | Single-process MCP server, sequential request handling |
