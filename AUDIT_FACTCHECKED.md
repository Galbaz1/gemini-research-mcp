# Audit Report (Fact-Checked)

Date: 2026-02-27
Workspace: `/Users/fausto/code_projects_work/gemini-research-mcp`
Mode: Read-only audit (no code fixes applied)

## Scope

- `.mcp.json`
- `CLAUDE.md`
- `README.md`
- `SECURITY.md`
- `pyproject.toml`
- `src/video_research_mcp/` including `server.py`, `config.py`, `client.py`, `tools/`
- `skills/video-research/SKILL.md`
- `skills/gemini-visualize/SKILL.md`
- `tests/`
- Installer and plugin structure for MCP/config reliability: `.claude-plugin/`, `bin/`

## Skill Activation (Used in This Review)

- `code-review-excellence`: severity-first, evidence-based review method.
- `MCP Integration`: `.mcp.json` and installer MCP merge/remove logic.
- `Plugin Structure`: plugin manifest and command/agent/skill contracts.
- `Plugin Settings`: local settings storage and ignore hygiene.

## Verification Log

1. Test suite:
   - Command: `uv run pytest tests/ -q`
   - Result: `154 passed in 1.97s`
2. Lint:
   - Command: `uv run ruff check src/ tests/`
   - Result: `All checks passed!`
3. Tool surface count evidence:
   - Command: `rg -n "@..._server.tool" src/video_research_mcp/tools/*.py`
   - Result: 14 tool decorators found.
4. Security/reliability pattern checks:
   - Commands: `rg -n` on MCP config, uninstall semantics, file-path ingestion/upload, command tool contracts.
5. Blocked checks:
   - `uv run pip-audit` failed: executable not installed.
   - `npm audit --omit=dev --json` failed: no lockfile (`ENOLOCK`).

## Findings

## P1

### P1-1 Unpinned MCP runtime dependencies create supply-chain drift risk

- Confidence: 0.96
- Impact: High
- Evidence:
  - `.mcp.json:4` uses `uvx` without pinned package version.
  - `.mcp.json:13` uses `@playwright/mcp@latest`.
  - `bin/lib/config.js:10` and `bin/lib/config.js:16` install same unpinned commands.
- Fact basis: exact config strings inspected in repo.
- Recommendation:
  - Pin explicit versions for both MCP server commands in `.mcp.json` and installer defaults.
  - Add release process rule for controlled updates.

### P1-2 Unrestricted local file ingestion and upload path

- Confidence: 0.84
- Impact: High
- Evidence:
  - `src/video_research_mcp/tools/content.py:39` opens arbitrary `file_path`.
  - `src/video_research_mcp/tools/content.py:43` reads bytes directly for model input.
  - `src/video_research_mcp/tools/video_file.py:51` resolves user path but does not enforce allowed roots.
  - `src/video_research_mcp/tools/video_file.py:97` uploads file to external API for large video handling.
  - `SECURITY.md:17` confirms local file access is process-user scoped (no stricter app guardrails).
- Inference (explicit): any readable local file path accepted by tool invocation can be sent to model APIs.
- Recommendation:
  - Add allowlisted roots and denylist sensitive paths.
  - Add explicit max-size/type restrictions for non-video content.
  - Add audit logging for file-source decisions (without secrets).

## P2

### P2-1 Uninstall removes MCP entries by name, not ownership/provenance

- Confidence: 0.92
- Impact: Medium-High
- Evidence:
  - `bin/lib/config.js:74-76` deletes `existing.mcpServers[name]` for known names with no ownership marker check.
- Fact basis: direct code path in uninstall helper.
- Recommendation:
  - Track installer-owned entries (metadata key/signature) and only remove owned entries.
  - Keep user-defined entry untouched when values differ.

### P2-2 Command contract mismatch: `AskUserQuestion` used but not allowed in frontmatter

- Confidence: 0.89
- Impact: Medium
- Evidence:
  - `commands/analyze.md:107` references `AskUserQuestion`, absent in `commands/analyze.md:4` allowed-tools.
  - `commands/research.md:121` references `AskUserQuestion`, absent in `commands/research.md:4`.
  - `commands/video-chat.md:131` references `AskUserQuestion`, absent in `commands/video-chat.md:4`.
  - `commands/video.md:175` references `AskUserQuestion`, absent in `commands/video.md:4`.
- Recommendation:
  - Align command body and frontmatter contracts.
  - Add CI lint rule: every referenced tool must be declared in `allowed-tools`.

### P2-3 URL content path bypasses model-level schema validation

- Confidence: 0.78
- Impact: Medium
- Evidence:
  - `src/video_research_mcp/tools/content.py:110` sets default schema.
  - `src/video_research_mcp/tools/content.py:121-137` URL path returns `json.loads(raw)` directly.
  - Model-validated default path exists for non-URL branch at `src/video_research_mcp/tools/content.py:166-171`.
- Inference (explicit): schema drift can pass through in URL path when raw JSON is parseable but shape-invalid.
- Recommendation:
  - Validate URL-path default output through `ContentResult.model_validate(...)` before returning.

## P3

### P3-1 Documentation drift on tool count and capabilities

- Confidence: 0.98
- Impact: Low-Medium
- Evidence:
  - README claims 11 tools: `README.md:90`, `README.md:222`.
  - CLAUDE.md claims 13 tools and also "All 11 tools carry ToolAnnotations": `CLAUDE.md:7`, `CLAUDE.md:61`, `CLAUDE.md:71`.
  - Actual decorator count is 14 from `src/video_research_mcp/tools/*.py`.
- Recommendation:
  - Generate tool inventory from code in CI and assert doc consistency.

### P3-2 Local settings file is not covered by ignore pattern

- Confidence: 0.85
- Impact: Low
- Evidence:
  - `.gitignore:10` ignores only `.claude/*.local.md`.
  - `.claude/settings.local.json` exists and is untracked in git status.
- Recommendation:
  - Extend ignore rules for `.claude/*.local.json` or specifically `.claude/settings.local.json`.

### P3-3 Version drift across package metadata

- Confidence: 0.88
- Impact: Low
- Evidence:
  - `pyproject.toml:3` is `0.1.0`.
  - `package.json:3` is `0.2.0`.
  - `.claude-plugin/plugin.json:3` is `0.2.0`.
- Recommendation:
  - Enforce single source of truth or release-time sync check for versions.

### P3-4 Test coverage gap for installer/config merge/remove behavior

- Confidence: 0.90
- Impact: Low-Medium
- Evidence:
  - No tests found referencing installer/config merge paths:
    - query `rg -n "bin/install.js|bin/lib/config.js|FILE_MAP|manifest" tests` returned no matches.
- Recommendation:
  - Add unit tests for `mergeConfig`, `removeFromConfig`, `computeActions`, and install/uninstall edge cases.

## Recommendations (Prioritized)

1. P1: Pin MCP runtime dependencies (`uvx` target and Playwright MCP version).
2. P1: Add file-path security guardrails (allowlist roots, sensitive-path denylist, size/type policy).
3. P2: Make uninstall ownership-aware for MCP entries.
4. P2: Fix command contract mismatches and enforce via CI lint.
5. P2: Enforce schema validation consistency for URL analysis path.
6. P3: Add installer/config tests in `tests/` for merge/remove safety.
7. P3: Add doc consistency checks for tool count and test count.
8. P3: Align version metadata across Python/npm/plugin manifests.
9. P3: Extend `.gitignore` for local JSON settings files.

## Blockers and Residual Risk

- Dependency vulnerability scanning is incomplete:
  - Python CVE scan blocked (`pip-audit` missing).
  - npm CVE scan blocked (no npm lockfile).
- Residual risk remains on supply-chain and local-file exposure until P1 actions are implemented.

---

## Weaviate Agent Skills Audit — Implementation Results

**Date**: 2026-02-27
**Reference**: Official Weaviate Agent Skills v0.2.1 (`weaviate@weaviate-plugins`)
**Our stack**: `weaviate-client` 4.20.1, 7 collections, sync client via `asyncio.to_thread`

### What Was Audited

Our Weaviate integration was independently built. This audit compared our approach against the canonical patterns published in the official Weaviate Agent Skills (collection creation, search modes, import, filtering, client lifecycle).

### Findings Implemented (5 commits)

| Finding | Severity | Status | Commits |
|---------|----------|--------|---------|
| Missing index flags (range, searchable) on properties | **High** | **Fixed** | `d5cf652`, `f1e0bc2` |
| No client timeout configuration | **Medium** | **Fixed** | `f788a66` |
| Collection creation via REST dict (`create_from_dict`) | **Low** | **Fixed** | `f788a66` |
| No keyword/semantic search modes | **Medium** | **Fixed** | `243a50e` |
| No fetch-by-UUID tool | **Medium** | **Fixed** | `243a50e` |

#### 1. Index Flags on Collection Properties (Critical)

**Problem**: `PropertyDef` had no `index_filterable`, `index_range_filters`, or `index_searchable` fields. Date/numeric range filters (`>`, `<`, `between`) on fields like `created_at`, `view_count`, `confidence` were either broken or doing full scans. JSON blob text fields (`raw_result`, `timestamps_json`, `sources_json`) polluted BM25 keyword results.

**Fix**: Added 3 index fields to `PropertyDef`. Set `index_range_filters=True` on 7 date/numeric fields (`created_at`, `view_count`, `like_count`, `comment_count`, `duration_seconds`, `confidence`, `turn_index`). Set `index_searchable=False` on 19 metadata/JSON text fields across all 7 collections.

**Files**: `weaviate_schema.py`

#### 2. Client Timeout Configuration (High)

**Problem**: All three connection paths (local, cloud, custom) used Weaviate defaults with no explicit timeouts, risking failures on slow networks or large queries.

**Fix**: Added `AdditionalConfig(timeout=Timeout(init=30, query=60, insert=120))` to all connection methods, matching the Weaviate Agent Skills pattern.

**Files**: `weaviate_client.py`

#### 3. v4 Property API Migration (Low)

**Problem**: `create_from_dict()` is a v3 compatibility shim that cannot express index flags. The v4 `Property()` constructor is type-checked and supports all config natively.

**Fix**: Replaced `create_from_dict(col_def.to_dict())` with `client.collections.create(name=..., properties=[Property(...)])`. Extracted `_to_property()` helper shared by both `ensure_collections` (create) and `_evolve_collection` (evolve).

**Files**: `weaviate_client.py`

#### 4. Search Modes (Medium)

**Problem**: `knowledge_search` only exposed `collection.query.hybrid()`. No way to do pure semantic search (`near_text`) or pure keyword search (`bm25`), which behave differently from hybrid at extreme alpha values.

**Fix**: Added `search_type: Literal["hybrid", "semantic", "keyword"]` parameter. Dispatches to `hybrid()`, `near_text()`, or `bm25()` with appropriate metadata extraction (score vs 1-distance).

**Files**: `tools/knowledge.py`

#### 5. Fetch-by-UUID Tool (Medium)

**Problem**: No way to retrieve a known object by UUID — a basic retrieval primitive missing from the tool surface.

**Fix**: Added `knowledge_fetch` tool with `object_id` and `collection` params. Returns `KnowledgeFetchResult` with `found`, `properties`, and `object_id`.

**Files**: `tools/knowledge.py`, `models/knowledge.py`

### Findings Deferred

| Finding | Severity | Reason |
|---------|----------|--------|
| No Query Agent integration (`weaviate-agents`) | Medium | Significant dependency addition, separate milestone |
| No data exploration tool (per-property metrics) | Low | Nice-to-have, not a gap |
| No `target_vector` for named vectors | Low | Not needed until multi-vector collections |
| No `properties` param on search | Low | Limits precision, but not blocking |
| Hybrid alpha default 0.5 vs 0.7 | Low | Preference — 0.5 is a reasonable balanced default |
| `insert_many` vs `batch.dynamic()` | Low | Our batch sizes are tiny (5-15 objects); `insert_many` is appropriate |

### Verification

```
uv run pytest tests/ -v     →  303 passed (was 279 before audit)
uv run ruff check src/ tests/  →  All checks passed!
```

24 new tests cover: index flags on all collections, `_to_property` conversion, timeout config on all connection paths, v4 `create()` API migration, `search_type` dispatch to hybrid/semantic/keyword, `knowledge_fetch` found/not-found/error paths.
