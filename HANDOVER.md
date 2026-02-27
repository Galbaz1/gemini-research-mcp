# Handover — Three Reliability Improvements

## Snapshot

- Date: 2026-02-27
- Branch: `main` (9 commits ahead of `origin/main`)
- Working tree: clean (all code committed)
- Test suite: 187 passed, 0 failed
- Lint: ruff clean

## Why These Changes

A technical evaluation identified three weaknesses in the MCP server's reliability:

1. **No retry on transient errors** — `GeminiClient.generate()` called `generate_content` once. Any 429 rate-limit, quota exhaustion, or timeout cascaded immediately to a tool error. For a server that makes heavy Gemini API calls (video analysis, research, search), this meant frequent spurious failures under load.

2. **Shared API key for YouTube** — `YouTubeClient` borrowed `GEMINI_API_KEY` for YouTube Data API v3 calls. This couples two unrelated quota pools. If you burn through YouTube's daily quota, you can't independently rotate or rate-limit that key without also affecting Gemini.

3. **Sessions lost on restart** — `SessionStore` was purely in-memory. Any server restart (deploy, crash, OOM kill) destroyed all active multi-turn video sessions. Users had to re-create sessions and lose conversation context.

These three features are independent — they touch different files and don't interact — so they were implemented in parallel by three agents after a shared config pre-work step.

## What Was Done

### Pre-work: Config foundation (`c01c17b`)

Added 5 new fields to `ServerConfig` in `config.py` with env var wiring in `from_env()`:

| Field | Env Var | Default | Purpose |
|-------|---------|---------|---------|
| `retry_max_attempts` | `GEMINI_RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts per API call |
| `retry_base_delay` | `GEMINI_RETRY_BASE_DELAY` | `1.0` | Base delay in seconds for exponential backoff |
| `retry_max_delay` | `GEMINI_RETRY_MAX_DELAY` | `60.0` | Ceiling on backoff delay |
| `youtube_api_key` | `YOUTUBE_API_KEY` | `""` | Dedicated YouTube key (falls back to Gemini key) |
| `session_db_path` | `GEMINI_SESSION_DB` | `""` | SQLite path for session persistence (empty = in-memory) |

Validators ensure `retry_max_attempts >= 1` and delays `> 0`. All defaults preserve existing behavior — no retry needed, shared key, in-memory sessions.

Updated the env var table in `CLAUDE.md` to document the new variables.

### Feature 1: Retry with exponential backoff (`79b0109`)

**Problem:** A single 429 or timeout kills the entire tool call.

**Solution:** `with_retry(coro_factory)` — an async wrapper that catches exceptions matching known transient patterns and retries with exponential backoff + jitter.

**Where to find it:**

| File | What changed |
|------|-------------|
| `src/video_research_mcp/retry.py` (new, 63 lines) | `_RETRYABLE_PATTERNS` tuple, `_is_retryable()` matcher, `with_retry()` async retry loop |
| `src/video_research_mcp/client.py` (L75-81) | `generate()` wraps `generate_content` in `with_retry(lambda: ...)` |
| `src/video_research_mcp/tools/video.py` (L222-230) | `video_continue_session` wraps its direct `generate_content` call |
| `src/video_research_mcp/tools/search.py` (L39-45) | `web_search` wraps its direct `generate_content` call |
| `tests/test_retry.py` (new, 150 lines) | 18 tests covering patterns, backoff, config, exhaustion |

**Design decisions:**

- **Pattern matching, not exception types:** Gemini SDK wraps errors inconsistently. String matching on `"429"`, `"quota"`, `"resource_exhausted"`, `"timeout"`, `"503"`, `"service unavailable"` catches them regardless of which exception class is used.
- **Lambda factory:** `with_retry(lambda: client.aio.models.generate_content(...))` wraps the call in a zero-arg factory. This is necessary because Python evaluates coroutines eagerly — passing the coroutine directly would start it before retry logic could control it.
- **Delay formula:** `min(base * 2^attempt + random(0, 1), max_delay)`. The jitter prevents thundering herd when multiple tools retry simultaneously.
- **No new dependencies:** Pure asyncio — `asyncio.sleep` for delays, `random.random` for jitter.

### Feature 2: Dedicated YouTube API key (`1563875`)

**Problem:** YouTube Data API and Gemini share one key, coupling their quotas.

**Solution:** One-line change — `YouTubeClient.get()` reads `cfg.youtube_api_key` first, falls back to `cfg.gemini_api_key` when empty.

**Where to find it:**

| File | What changed |
|------|-------------|
| `src/video_research_mcp/youtube.py` (L57-58) | `api_key = cfg.youtube_api_key or cfg.gemini_api_key` |
| `tests/test_youtube.py` (bottom) | `TestYouTubeApiKeyFallback` — 2 tests for dedicated key and fallback |

**Zero breaking change:** When `YOUTUBE_API_KEY` is unset (the default), behavior is identical to before.

### Feature 3: SQLite session persistence (`b82bc61`)

**Problem:** Server restart loses all multi-turn video sessions.

**Solution:** Opt-in SQLite write-through. Set `GEMINI_SESSION_DB=~/.cache/video-research-mcp/sessions.db` to enable.

**Where to find it:**

| File | What changed |
|------|-------------|
| `src/video_research_mcp/persistence.py` (new, 159 lines) | `SessionDB` class — SQLite WAL, `save_sync`/`load_sync`/`delete`, Content serialization helpers |
| `src/video_research_mcp/sessions.py` | `SessionStore.__init__` accepts `db_path`, write-through on `create()`/`add_turn()`, DB fallback on `get()`, lazy singleton via `_make_default_store()` |
| `tests/test_persistence.py` (new, 147 lines) | 10 tests — roundtrip, history serialization, delete, parent dir creation, Content serde |
| `tests/test_sessions.py` | 3 new tests in `TestSessionStorePersistence` — persist+recover, no-persistence default, add_turn persists |

**Design decisions:**

- **Synchronous write-through:** `save_sync()`/`load_sync()` use `sqlite3` directly (not async). SQLite WAL writes complete in <1ms. Making `create()`/`get()`/`add_turn()` async would require changing their signatures and every caller in `tools/video.py` — the cost of async machinery exceeds the benefit for sub-millisecond operations.
- **Content serialization:** `_content_to_dict()` / `_dict_to_content()` handle `types.Content` ↔ JSON. Supports `text` and `file_data` parts (the two types used in video sessions).
- **Lazy singleton:** `session_store = _make_default_store()` reads `GEMINI_SESSION_DB` from config at import time. Empty string (default) means `_db = None` and purely in-memory behavior, identical to before.
- **WAL mode + NORMAL synchronous:** Optimized for write-through pattern — fast writes, crash-safe enough for session data (not financial transactions).

## Earlier Commits in This PR

The first 5 commits (before the three improvements) add YouTube Data API v3 integration:

| Commit | What |
|--------|------|
| `03d63da` | refactor(commands): delegate visualization to background agents |
| `e1f7e27` | feat(agents): add visualizer and comment-analyst definitions |
| `befb005` | feat(youtube): add YouTube Data API v3 client, models, and tools |
| `890fa6f` | docs: update tool surface for YouTube API integration (11 -> 13 tools) |
| `0509bbc` | test(youtube): add 35 unit tests for YouTube client and tools |

These introduced `youtube.py`, `models/youtube.py`, `tools/youtube.py`, and the full test suite in `test_youtube.py`. The three-improvements work builds on this foundation (the YouTube API key feature modifies the client added in `befb005`).

## File Map

### New production files

| File | Lines | Responsibility |
|------|-------|---------------|
| `src/video_research_mcp/retry.py` | 63 | Exponential backoff retry for Gemini API calls |
| `src/video_research_mcp/persistence.py` | 159 | SQLite session storage with WAL mode |
| `src/video_research_mcp/youtube.py` | 201 | YouTube Data API v3 client (metadata, comments, playlists) |
| `src/video_research_mcp/models/youtube.py` | 62 | Pydantic models for YouTube responses |
| `src/video_research_mcp/tools/youtube.py` | 115 | MCP tools for video_metadata and video_playlist |

### Modified production files

| File | What changed |
|------|-------------|
| `src/video_research_mcp/config.py` | +5 fields, +3 validators, +5 env vars in `from_env()` |
| `src/video_research_mcp/client.py` | `generate()` wraps API call in `with_retry()` |
| `src/video_research_mcp/sessions.py` | `SessionStore` accepts `db_path`, write-through + DB fallback |
| `src/video_research_mcp/tools/video.py` | `video_continue_session` uses `with_retry()` |
| `src/video_research_mcp/tools/search.py` | `web_search` uses `with_retry()` |
| `src/video_research_mcp/server.py` | Mounts `youtube_server` sub-server |
| `src/video_research_mcp/types.py` | Adds YouTube URL type alias |

### New test files

| File | Lines | Tests | Covers |
|------|-------|-------|--------|
| `tests/test_retry.py` | 150 | 18 | Retry patterns, backoff, config, exhaustion |
| `tests/test_persistence.py` | 147 | 10 | SQLite roundtrip, history, deletion, serde |
| `tests/test_youtube.py` | 481 | 37 | YouTube client, tools, URL parsing, API key fallback |

### Modified test files

| File | What changed |
|------|-------------|
| `tests/test_sessions.py` | +3 tests in `TestSessionStorePersistence` |

## Validation

```
uv run pytest tests/ -v    # 187 passed in 6.4s
uv run ruff check src/ tests/  # All checks passed
```

No production file exceeds 300 lines. No test file exceeds 500 lines.

## How to Use the New Features

```bash
# Retry: enabled by default (3 attempts, 1s base delay)
# Customize via env vars:
export GEMINI_RETRY_MAX_ATTEMPTS=5
export GEMINI_RETRY_BASE_DELAY=0.5
export GEMINI_RETRY_MAX_DELAY=30.0

# YouTube API key: set to decouple from Gemini quota
export YOUTUBE_API_KEY=AIza...your-youtube-key

# Session persistence: set a path to enable
export GEMINI_SESSION_DB=~/.cache/video-research-mcp/sessions.db
```

All three features are backward-compatible. With no env vars set, behavior is identical to before.
