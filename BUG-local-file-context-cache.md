# BUG: Context caching not triggered for local file sessions

**Reported**: 2026-02-28
**Severity**: MEDIUM (functional workaround exists — sessions work without cache, but at higher cost per turn)
**Reproducible**: Yes — 100% on two different local files

## Summary

`video_create_session(file_path=...)` creates functional sessions for local files, but context caching is never activated. The `cache_status` field always returns `"uncached"` and `cache_reason` is empty. This means every `video_continue_session` turn re-ingests the full video, increasing latency and Gemini API cost per turn.

## Reproduction Steps

```python
# Step 1: Create session with local file
video_create_session(file_path="/path/to/video.mp4", description="test")
# Returns: cache_status="uncached", cache_reason="", download_status=""

# Step 2: Use session (works, but uncached)
video_continue_session(session_id="...", prompt="summarize")
# Returns: correct response, turn_count=1

# Step 3: Check cache registry
infra_cache(action="context")
# Returns: registry has NO entry for local file (only YouTube videos present)
```

## Test Evidence

### Test 1: Small local file (docs-720p.mp4, ~10 MB, 3:30 duration)
- `video_create_session(file_path=".../docs-720p.mp4")` → `cache_status: "uncached"`, `cache_reason: ""`
- 2 turns of `video_continue_session` — both work, context maintained across turns
- `infra_cache(action="context")` after 2 turns — no entry for this file

### Test 2: Large local file (call_terrence_fausto.mp4, 295 MB, ~45 min duration)
- `video_create_session(file_path=".../call_terrence_fausto.mp4")` → `cache_status: "uncached"`, `cache_reason: ""`
- 1 turn of `video_continue_session` — works, detailed response
- `infra_cache(action="context")` — still no entry

### Control: YouTube video (context cache works)
- `video_create_session(url="https://www.youtube.com/watch?v=GcNu6wrLTJc")` → `cache_status: "uncached"` (expected without `download=True`)
- But `video_analyze(url=...)` for the same video DID populate the context cache registry: `GcNu6wrLTJc/gemini-3.1-pro-preview → cachedContents/dedup-789`

## Expected Behavior

For local files, `video_create_session` should:
1. Upload the file to Gemini File API (if not already uploaded)
2. Call `ensure_session_cache()` to create a context cache
3. Return `cache_status: "cached"` with a populated `cache_reason`
4. Register the cache in `infra_cache(action="context")` registry

## Likely Root Cause

Based on the file structure, the caching codepath likely lives in:

| File | Role |
|------|------|
| `src/video_research_mcp/context_cache.py` | Core caching logic, `ensure_session_cache()` |
| `src/video_research_mcp/sessions.py` | Session management, session creation |
| `src/video_research_mcp/tools/video_cache.py` | Cache tool (`infra_cache`) |

Hypothesis: `video_create_session` in `sessions.py` does NOT call `ensure_session_cache()` for local files. The PR #11 notes state that `ensure_session_cache()` "still exists for non-YouTube (File API URI) use cases" — but it may not be wired up in the session creation flow for local `file_path` inputs.

The YouTube `download=True` path (PR #11) explicitly handles: download → File API upload → cache creation. But the local file path may be missing the equivalent: File API upload → cache creation.

## Impact

- **Cost**: Each `video_continue_session` turn re-sends the full video to Gemini, costing full input tokens per turn instead of using cached context
- **Latency**: Larger files (295 MB call recording) have noticeably higher latency per turn
- **Functionality**: Sessions work correctly — this only affects efficiency

## Suggested Fix Direction

In `sessions.py` (or wherever `video_create_session` is implemented for local files):
1. After session creation, upload the local file to Gemini File API
2. Call `ensure_session_cache()` with the File API URI
3. Populate `cache_status`, `cache_reason` in the response
4. Register in the context cache registry

## Environment

- video-research-mcp: v0.2.0 (local dev, `uv run`)
- Gemini model: `gemini-3.1-pro-preview` (best preset)
- macOS Darwin 25.2.0
- Python 3.12
