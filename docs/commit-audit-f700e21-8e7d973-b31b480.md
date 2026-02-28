# Executive Summary
This audit reviewed commits `f700e21`, `8e7d973`, and `b31b480` as one change set across six rounds, with repository-wide tracing and Gemini documentation validation.

Result: 5 findings.
- High: 2
- Medium: 2
- Low: 1

Top risks:
1. Context-cache persistence added in `f700e21` is largely neutralized by unconditional cache clearing at server shutdown.
2. New bridge tests in `b31b480` are not executable under current FastMCP tool semantics (`FunctionTool` not directly callable), so expected protection is not active.

# Scope and Method
- Fixed audit scope commits:
1. `f700e21` (`src/video_research_mcp/context_cache.py`)
2. `8e7d973` (`src/video_research_mcp/tools/video.py`, `src/video_research_mcp/tools/video_batch.py`)
3. `b31b480` (`tests/test_context_cache.py`, `tests/test_cache_bridge.py`)
- Repository context reviewed beyond touched files:
1. `src/video_research_mcp/server.py`
2. `src/video_research_mcp/sessions.py`
3. `src/video_research_mcp/persistence.py`
4. `src/video_research_mcp/tools/video_url.py`
5. `tests/conftest.py`
6. `tests/test_video_tools.py`
- Validation methods:
1. Commit metadata/diff inspection (`git show`, `git log`, `rg`, line-level inspection)
2. Targeted test execution (`PYTHONPATH=src pytest -q tests/test_context_cache.py tests/test_cache_bridge.py`)
3. Gemini official docs cross-check for caching/video behavior and API field constraints

# Round-by-Round Results
## Round 1: Commit Inventory & Intent Validation
- Commit inventory validated:
1. `f700e21`: persistence and lazy load for context cache registry (+51 LOC)
2. `8e7d973`: bridge prewarm/lookup/consume flow and batch tool extraction (+174/-103 LOC)
3. `b31b480`: persistence + bridge tests (+367 LOC)
- Intent appears coherent with commit messages and code deltas.
- No metadata anomalies found.

## Round 2: Commit-Level Correctness Review
- `f700e21`:
1. Registry persistence and lazy load are implemented as described.
2. Found stale-entry persistence defect when recreation fails (F-004).
- `8e7d973`:
1. Cache bridge wiring is functionally connected (analyze -> lookup -> continue).
2. Found async handoff race between prewarm and session creation (F-002).
- `b31b480`:
1. Tests are comprehensive in scenario intent.
2. Execution model mismatch makes new tests non-runnable as written in current environment (F-003).

## Round 3: Cross-Commit Interaction Review
- Interaction path analyzed: `video_analyze` prewarm -> `context_cache` registry -> `video_create_session` lookup -> `video_continue_session` `cached_content`.
- Main interaction gap: graceful server shutdown clears persisted cache registry and remote caches, undermining restart benefit from `f700e21` (F-001).
- Positive note: `video_continue_session` model selection (`session.model`) aligns with cache/model binding constraints from Gemini API.

## Round 4: Codebase-Wide Impact Review
- Traced call sites in `server.py`, `sessions.py`, `persistence.py`, `video_url.py`, and related tests.
- Architectural drift identified:
1. Persistence feature (`f700e21`) conflicts with lifecycle policy in `server.py` (F-001).
2. Registry mutation durability is inconsistent for stale eviction path (F-004).
- No additional duplicate-logic defects found in touched pathways.

## Round 5: Gemini Documentation Compliance Review
- Checked against official Gemini docs for:
1. Cached content lifecycle and explicit caching flow
2. Cached content immutability/update constraints
3. Video prompting best practices
- Compliance status:
1. Model binding handling in `video_continue_session` is aligned.
2. TTL refresh behavior (update only expiration) is aligned.
3. Found low-severity missed opportunity: no pre-check for model-specific minimum token thresholds before forced prewarm attempts (F-005).

## Round 6: Test Adequacy & Missed Opportunities
- 13 tests added in commit scope (4 persistence + 9 bridge behavior) are logically well-targeted.
- Adequacy issue:
1. Current invocation style treats decorated FastMCP tools as directly callable coroutines, causing runtime TypeErrors (F-003).
- Coverage gaps:
1. No test for graceful restart persistence behavior with server lifespan hooks.
2. No race test for immediate `video_analyze` -> `video_create_session` sequence.
3. No test ensuring stale-registry removal is persisted to disk on recreation failure.

# Consolidated Findings Table
| ID | Severity | Category | Commit(s) | Location | Summary |
|---|---|---|---|---|---|
| F-001 | High | Bug | `f700e21` | `src/video_research_mcp/server.py:28`, `src/video_research_mcp/context_cache.py:147-175` | Shutdown cache clear negates restart persistence objective. |
| F-002 | Medium | Regression Risk | `8e7d973` | `src/video_research_mcp/tools/video.py:185-193`, `src/video_research_mcp/tools/video.py:268-277` | Fire-and-forget prewarm races with immediate session creation lookup. |
| F-003 | High | Test Gap | `b31b480` | `tests/test_cache_bridge.py:73`, `:93`, `:106`, `:154` etc. | New tests call `FunctionTool` objects directly and fail at runtime. |
| F-004 | Medium | Maintainability | `f700e21` | `src/video_research_mcp/context_cache.py:92-95`, `:118-121` | Stale registry key removal is not persisted if recreate fails. |
| F-005 | Low | Documentation Compliance | `f700e21`, `8e7d973` | `src/video_research_mcp/context_cache.py:96-120`, `src/video_research_mcp/tools/video.py:185-193` | Prewarm path does not gate by documented explicit-cache minimum token thresholds. |

## Detailed Findings (Required Format)
### F-001
- `ID`: `F-001`
- `Severity`: High
- `Category`: Bug
- `Commit(s)`: `f700e21`
- `Location`: `src/video_research_mcp/server.py:28`; `src/video_research_mcp/context_cache.py:147-175`
- `Evidence`:
1. `f700e21` introduces disk-backed registry intended to survive restarts.
2. Server lifespan unconditionally calls `await context_cache.clear()` on shutdown (`server.py:28`).
3. `clear()` empties registry and writes persisted empty state (`context_cache.py:173-175`), and also deletes remote caches when client is available (`:167-171`).
- `Impact`: Graceful restart loses both local registry and remote cached content, so restart reuse is effectively unavailable in the normal shutdown path.
- `Recommendation`: Make shutdown clearing optional (config flag default `False`) or move it to explicit admin tooling; preserve persisted registry across normal restarts and perform selective GC by TTL/age instead.
- `Documentation Citation`: [https://ai.google.dev/gemini-api/docs/caching#how-explicit-caching-reduces-costs](https://ai.google.dev/gemini-api/docs/caching#how-explicit-caching-reduces-costs) — “How explicit caching reduces costs” (cache lifetime is TTL/expiration-driven, default 60 minutes if not specified).

### F-002
- `ID`: `F-002`
- `Severity`: Medium
- `Category`: Regression Risk
- `Commit(s)`: `8e7d973`
- `Location`: `src/video_research_mcp/tools/video.py:185-193`; `src/video_research_mcp/tools/video.py:268-277`
- `Evidence`:
1. `video_analyze` starts prewarm with `asyncio.create_task(...)` and does not await completion.
2. `video_create_session` performs immediate synchronous `context_cache.lookup(...)`.
3. Therefore, analyze->create_session in quick succession can observe `"uncached"` before prewarm finishes.
- `Impact`: Intermittent cache misses after successful analyze reduce latency/cost benefits and create nondeterministic user-facing `cache_status`.
- `Recommendation`: On lookup miss, perform a bounded await of `get_or_create` (or expose/return `cache_name` from analyze and pass it into session creation); add an integration test that executes immediate analyze->create_session handoff.
- `Documentation Citation`: [https://ai.google.dev/gemini-api/docs/caching#use-explicit-caching](https://ai.google.dev/gemini-api/docs/caching#use-explicit-caching) — “Use explicit caching” (documented flow creates cache first, then uses `cached_content`).

### F-003
- `ID`: `F-003`
- `Severity`: High
- `Category`: Test Gap
- `Commit(s)`: `b31b480`
- `Location`: `tests/test_cache_bridge.py:73`, `:93`, `:106`, `:154`, `:191`, `:216`, `:249`, `:278`, `:301`
- `Evidence`:
1. Tests call `await video_analyze(...)` / `await video_create_session(...)` / `await video_continue_session(...)` directly.
2. Runtime type is `fastmcp.tools.tool.FunctionTool` (not directly awaitable callable).
3. Executing `PYTHONPATH=src pytest -q tests/test_context_cache.py tests/test_cache_bridge.py` yields 9 failures with `TypeError: 'FunctionTool' object is not callable`.
- `Impact`: New bridge tests do not provide active regression protection; reported coverage does not translate to executable checks.
- `Recommendation`: Invoke wrapped functions via `.fn` (e.g., `await video_analyze.fn(...)`) or test through the MCP invocation layer used in production.
- `Documentation Citation`: N/A (repository/tooling execution issue, not Gemini API behavior).

### F-004
- `ID`: `F-004`
- `Severity`: Medium
- `Category`: Maintainability
- `Commit(s)`: `f700e21`
- `Location`: `src/video_research_mcp/context_cache.py:92-95`; `src/video_research_mcp/context_cache.py:118-121`
- `Evidence`:
1. On stale cache detection (`caches.get` exception), code removes key from in-memory registry (`_registry.pop(...)`).
2. If subsequent `caches.create` fails, function returns `None` without calling `_save_registry()`.
3. Persisted JSON can retain stale key and rehydrate it after restart.
- `Impact`: Repeated stale-key churn across process restarts creates avoidable API calls and warning noise, and drifts disk state from in-memory truth.
- `Recommendation`: Persist immediately after stale key eviction or maintain a mutation-dirty flag and flush at function end regardless of recreate success.
- `Documentation Citation`: N/A (internal state consistency defect).

### F-005
- `ID`: `F-005`
- `Severity`: Low
- `Category`: Documentation Compliance
- `Commit(s)`: `f700e21`, `8e7d973`
- `Location`: `src/video_research_mcp/context_cache.py:96-120`; `src/video_research_mcp/tools/video.py:185-193`
- `Evidence`:
1. Every successful YouTube `video_analyze` starts prewarm create attempts.
2. Code does not estimate/check input size before cache creation attempts.
3. Gemini caching docs define model-specific minimum token counts for explicit caching.
- `Impact`: Short-input prewarm attempts can fail predictably and generate extra API traffic/logging without user benefit.
- `Recommendation`: Add a lightweight gating heuristic (e.g., known-short clips, approximate token estimator, or fallback suppression after repeated minimum-threshold failures per content/model).
- `Documentation Citation`: [https://ai.google.dev/gemini-api/docs/caching#additional-considerations](https://ai.google.dev/gemini-api/docs/caching#additional-considerations) — “Additional considerations” (minimum token count per model for explicit caching).

# Missed Opportunities
1. The bridge could return `cache_name` (or warm status) from `video_analyze` to eliminate handoff ambiguity in `video_create_session`.
2. Lifecycle policy could separate “registry persistence” from “remote cache cleanup” via explicit infra control rather than unconditional shutdown deletion.
3. Cache registry serialization could include write versioning and schema validation for safer forward compatibility.
4. Test suite could include a real end-to-end MCP tool invocation path to catch wrapper/type API changes.

# Test Coverage Assessment
## What the 13 tests cover well
1. Registry persistence roundtrip, missing/corrupt file handling, and GC cap behavior.
2. Core bridge behaviors: prewarm trigger, cache hit/miss status, cached_content propagation, model selection, TTL-refresh fallback, and prompt-part composition.

## What is missing or weak
1. Executability gap: current direct invocation style fails under `FunctionTool` wrappers (F-003).
2. No test for graceful restart behavior involving `server._lifespan` + `context_cache.clear`.
3. No race test for immediate analyze->create_session sequence.
4. No assertion that stale key removal persists to disk when recreate fails.

## Practical confidence level
- Behavioral intent coverage: Moderate.
- Real regression-detection strength in current environment: Low until invocation semantics are fixed.

# Prioritized Remediation Plan
1. Fix test invocation semantics (`.fn` or MCP harness) and make `b31b480` tests pass in CI first (unblocks reliable feedback).
2. Resolve lifecycle conflict: stop unconditional shutdown cache clearing or guard it with explicit opt-in.
3. Fix stale-key persistence path by saving registry after stale eviction, even on create failure.
4. Remove bridge race by adding a bounded synchronous fallback in `video_create_session` when lookup misses.
5. Add token-threshold aware prewarm gating and tune log level for expected cache-create misses.

# Gemini Documentation Citations
1. [https://ai.google.dev/gemini-api/docs/caching](https://ai.google.dev/gemini-api/docs/caching) — “Context caching”, sections: “Use explicit caching”, “How explicit caching reduces costs”, “Additional considerations”.
2. [https://ai.google.dev/api/caching](https://ai.google.dev/api/caching) — “CachedContent”, fields and update constraints (model immutability; only expiration fields updatable).
3. [https://ai.google.dev/gemini-api/docs/video-understanding](https://ai.google.dev/gemini-api/docs/video-understanding) — “Video understanding”, sections: “Passing video data in prompt”, “Best practices for prompting with video”, “YouTube URLs”.

# Appendix (commit inventory and reviewed files)
## Commit inventory
1. `f700e21` — `feat(context-cache): add disk persistence with atomic writes and GC`
2. `8e7d973` — `feat(video): bridge context cache between analyze, sessions, and generate`
3. `b31b480` — `test(cache-bridge): add persistence and bridge integration tests`

## Files changed in scope commits
1. `src/video_research_mcp/context_cache.py`
2. `src/video_research_mcp/tools/video.py`
3. `src/video_research_mcp/tools/video_batch.py`
4. `tests/test_context_cache.py`
5. `tests/test_cache_bridge.py`

## Additional repository files reviewed for integration context
1. `src/video_research_mcp/server.py`
2. `src/video_research_mcp/sessions.py`
3. `src/video_research_mcp/persistence.py`
4. `src/video_research_mcp/tools/video_url.py`
5. `src/video_research_mcp/tools/video_core.py`
6. `src/video_research_mcp/tools/video_file.py`
7. `tests/conftest.py`
8. `tests/test_video_tools.py`
