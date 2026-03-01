# Test Strategy Audit — 2026-03-01

> Scope: PRs #10 (video-explainer), #12 (MLflow tracing), #16 (video-agent), #18 (Cohere reranker + Flash summarization), #19 (contract hardening pending).
> Current state: 540 tests across 34 files. All unit-level with mocked Gemini.

---

## 1. Documents Reviewed

| Document | Key Content |
|----------|-------------|
| `test_handover.md` | 41-scenario interactive test suite (v0.2.0). 6 tests executed (A1, A2, A3, G4, G5, F1). 35 remaining. Covers 23 tools, 8 commands, 4 agents |
| Test workspace `CLAUDE.md` | 45-item test menu for interactive testing. Key verification gotchas for phase ordering, parallelism, and caching behavior |
| `tracing.py` | 101 lines. Guarded MLflow import, `is_enabled()`, `trace()` decorator, `setup()`/`shutdown()` lifecycle |
| `summarize.py` | 92 lines. Flash post-processor: `_build_prompt()`, `_apply_summaries()`, `summarize_hits()`. Best-effort, caps at 20 hits |
| `search.py` | 205 lines. `knowledge_search` with 3 modes (hybrid/semantic/keyword), reranker integration, Flash post-processing pipeline |
| `knowledge_filters.py` | 84 lines. `build_collection_filter()` — collection-aware Weaviate Filter builder |
| `youtube_download.py` | 97 lines. `download_youtube_video()` via yt-dlp subprocess. Cache-aware, 720p max |
| `video_cache.py` | 153 lines. `prewarm_cache()`, `resolve_session_cache()`, `ensure_session_cache()`, `prepare_cached_request()` |
| `config.py` | 233 lines. `ServerConfig` with new fields: `reranker_enabled`, `reranker_provider`, `flash_summarize`, `tracing_enabled`, `mlflow_tracking_uri`, `mlflow_experiment_name` |
| `agent.py` | 186 lines. `knowledge_ask`/`knowledge_query` (deprecated) tools via AsyncQueryAgent |
| `helpers.py` | 50 lines. `RERANK_PROPERTY` map, `weaviate_not_configured()`, `serialize()` |
| `ingest.py` | 83 lines. `knowledge_ingest` with JSON string deserialization and schema validation |
| `models/knowledge.py` | 135 lines. `HitSummary`, `HitSummaryBatch` (new), `rerank_score`/`summary` fields on `KnowledgeHit` |
| `weaviate_client.py` | 320 lines. `_evolve_collection()` with reranker config, `_collect_provider_headers()`, `_aconnect()` |

---

## 2. Existing Unit Test Coverage

| Module | Test File | Tests | Coverage Assessment |
|--------|-----------|-------|---------------------|
| `tracing.py` | `test_tracing.py` | 15 | Good: `is_enabled`, `setup`, `shutdown`, `_resolve_tracing_enabled`. Covers enabled/disabled/error paths |
| `summarize.py` | `test_knowledge_summarize.py` | 7 | Good: enrichment, trimming, fallback, empty, batch cap, empty useful_properties, unmatched hits |
| `knowledge_filters.py` | `test_knowledge_filters.py` | 12 | Good: all filter types, skip logic, combined, invalid date, empty strings |
| `youtube_download.py` | `test_youtube_download.py` | 6 | Good: not-found, cached, success, failure, empty cache, target_dir |
| `search.py` (knowledge_search) | `test_knowledge_tools.py` | 39 | Good base coverage, but reranker + Flash pipeline paths are undertested |
| `agent.py` (knowledge_ask/query) | `test_knowledge_agent_tools.py` | 20 | Good: ask/query happy paths, weaviate-agents missing, weaviate disabled, agent cache |
| `config.py` | `test_config.py` | 7 | Thin: validators tested, but new fields (`reranker_enabled`, `flash_summarize`) logic not directly tested |
| `video_cache.py` | `test_cache_bridge.py` | 25 | Good: prewarm, resolve, ensure, prepare. YouTube skip, timeout, suppressed paths |
| `weaviate_client.py` | `test_weaviate_client.py` | 29 | Good base, but `_evolve_collection` reranker path and provider headers undertested |

---

## 3. Gap Analysis

### 3.1 Gaps Between Merged PRs and Existing Tests

| PR | Feature | Test Status | Gap |
|----|---------|-------------|-----|
| #18 | Cohere reranker in `knowledge_search` | Partial | `_build_rerank()` called when `cfg.reranker_enabled`, overfetch factor `3x`, `rerank_score` extraction, sort-by-rerank — no dedicated tests for the reranker pipeline path |
| #18 | Flash summarization in `knowledge_search` | Partial | `summarize.py` functions well-tested in isolation, but the integration path in `search.py` (cfg.flash_summarize check, flash_processed flag) has no test |
| #18 | `reranker_enabled` derivation in config | Missing | `from_env()` logic: `COHERE_API_KEY` presence auto-enables, `RERANKER_ENABLED=false` overrides — no test |
| #18 | `flash_summarize` config default | Missing | Default `true`, env override `FLASH_SUMMARIZE=false` — no test |
| #12 | `@trace()` decorator on tools | Partial | Decorator tested in `test_tracing.py`, but actual tool decoration (search, ingest, agent tools) not verified |
| #12 | `_resolve_tracing_enabled()` edge cases | Good | 6 tests cover all cases |
| #16 | `RERANK_PROPERTY` map completeness | Missing | 11 collections defined, but no test verifies all collections have a rerank property or that keys match `ALL_COLLECTION_NAMES` |
| #19 | `knowledge_query` deprecation behavior | Missing | `_deprecated` and `_deprecation_notice` fields added to return dict — no test |
| #19 | `KnowledgeSearchResult.reranked`/`flash_processed` flags | Missing | New boolean fields on model — no test verifying they propagate from search pipeline |

### 3.2 Gaps Between Test Handover and Unit Tests

The test handover defines 41 interactive scenarios. Of these, the unit test suite covers the **tool-level behavior** for most, but several behavioral contracts from the handover have no unit-level equivalent:

| Handover Scenario | Gap |
|-------------------|-----|
| E1: Three search modes return different rankings | No test comparing result ordering across modes |
| E6/E7: QueryAgent graceful errors | Covered |
| G2: Graceful degradation (no Weaviate) | Covered per-tool, but no cross-tool integration test |
| G4a-d: Context cache session variants | `test_cache_bridge.py` covers the building blocks but not the full `video_create_session` flow with download=True |
| A8b: `/gr:recall` ask mode | Interactive-only (command behavior, not tool) |

### 3.3 Structural Gaps

1. **No integration test for the reranker+Flash pipeline end-to-end** — `search.py` calls `_build_rerank()`, dispatches with rerank config, extracts rerank_score, sorts by it, then optionally calls `summarize_hits()`. Each piece is tested, but the composed pipeline is not.

2. **`_dispatch_search` receives rerank_cfg but no test verifies it reaches the Weaviate query method** — the mock in `test_knowledge_tools.py` stubs `collection.query.hybrid()` etc. but doesn't assert that `rerank=` kwarg is passed.

3. **`WeaviateClient._evolve_collection` reranker path** — when `reranker_enabled=True`, calls `col.config.update(reranker_config=...)`. Only tested implicitly through `ensure_collections`.

4. **`_collect_provider_headers`** — scans env for OPENAI, COHERE, etc. API keys and adds as Weaviate headers. No test.

5. **Config `from_env()` for new fields** — `reranker_enabled` has complex derivation (COHERE_API_KEY + RERANKER_ENABLED flag). `flash_summarize` has env override. Neither tested.

---

## 4. Prioritized Test Scenarios

### HIGH Priority (Behavioral correctness of new features)

#### H1. `knowledge_search` reranker pipeline integration
**Scenario**: Search with `reranker_enabled=True` produces reranked results.
- **Setup**: Mock config with `reranker_enabled=True`. Mock Weaviate collection to return objects with `rerank_score` in metadata.
- **Verify**: (a) `_build_rerank()` called with correct property from `RERANK_PROPERTY`, (b) `rerank=` kwarg passed to `collection.query.hybrid()`, (c) fetch limit is `limit * 3`, (d) results sorted by `rerank_score` descending, (e) `KnowledgeSearchResult.reranked == True`.
- **File**: `test_knowledge_tools.py`

#### H2. `knowledge_search` Flash summarization integration
**Scenario**: Search with `flash_summarize=True` enriches hits.
- **Setup**: Mock config with `flash_summarize=True`. Mock `GeminiClient.generate_structured()` to return `HitSummaryBatch`.
- **Verify**: (a) `summarize_hits()` called after search, (b) `flash_processed == True` in result, (c) hits have `summary` field populated.
- **File**: `test_knowledge_tools.py`

#### H3. `knowledge_search` reranker + Flash combined
**Scenario**: Both reranker and Flash enabled simultaneously.
- **Setup**: Both `reranker_enabled=True` and `flash_summarize=True`.
- **Verify**: Reranking happens first (in Weaviate query), then Flash post-processes. `reranked=True`, `flash_processed=True`. Sort order preserved after Flash.
- **File**: `test_knowledge_tools.py`

#### H4. `knowledge_search` reranker disabled path
**Scenario**: Search with `reranker_enabled=False`.
- **Verify**: (a) `rerank=None` passed to Weaviate query, (b) fetch limit equals `limit` (no overfetch), (c) `reranked=False`.
- **File**: `test_knowledge_tools.py`

#### H5. Config `reranker_enabled` derivation from env
**Scenario**: Test all combinations of `COHERE_API_KEY` and `RERANKER_ENABLED`.
- `COHERE_API_KEY=xxx`, no flag -> `True`
- `COHERE_API_KEY=xxx`, `RERANKER_ENABLED=false` -> `False`
- `COHERE_API_KEY=xxx`, `RERANKER_ENABLED=true` -> `True`
- No `COHERE_API_KEY`, `RERANKER_ENABLED=true` -> `True`
- No `COHERE_API_KEY`, no flag -> `False`
- **File**: `test_config.py`

#### H6. Config `flash_summarize` env override
**Scenario**: `FLASH_SUMMARIZE` env var controls behavior.
- Default (unset) -> `True`
- `FLASH_SUMMARIZE=false` -> `False`
- `FLASH_SUMMARIZE=true` -> `True`
- **File**: `test_config.py`

#### H7. `_extract_score` with rerank_score
**Scenario**: `_extract_score` returns correct `(base_score, rerank_score)` tuple.
- Semantic: base = `1.0 - distance`, rerank from metadata
- Keyword/Hybrid: base = metadata.score, rerank from metadata
- No rerank_score: returns `(base, None)`
- **File**: `test_knowledge_tools.py`

### MEDIUM Priority (Robustness and edge cases)

#### M1. `_dispatch_search` passes rerank config correctly
**Scenario**: All three search modes (hybrid, semantic, keyword) forward `rerank_cfg` to Weaviate.
- **Verify**: For each mode, the correct query method receives `rerank=rerank_cfg` kwarg.
- **File**: `test_knowledge_tools.py`

#### M2. `knowledge_search` Flash failure doesn't break search
**Scenario**: `flash_summarize=True` but Flash call raises exception.
- **Verify**: Returns raw hits (no crash), `flash_processed=False`.
- **Note**: `summarize_hits` already tested in isolation for this, but the integration in `search.py` should verify the flag.
- **File**: `test_knowledge_tools.py`

#### M3. `RERANK_PROPERTY` map covers all collections
**Scenario**: Every collection in `ALL_COLLECTION_NAMES` has an entry in `RERANK_PROPERTY`.
- **Verify**: `set(RERANK_PROPERTY.keys()) == set(ALL_COLLECTION_NAMES)`
- **File**: `test_knowledge_tools.py` (or `test_knowledge_helpers.py` if split)

#### M4. `knowledge_query` deprecation fields
**Scenario**: `knowledge_query` returns `_deprecated=True` and `_deprecation_notice`.
- **Verify**: Both fields present in return dict.
- **File**: `test_knowledge_agent_tools.py`

#### M5. `_collect_provider_headers` in `weaviate_client.py`
**Scenario**: Various API keys in environment produce correct Weaviate headers.
- `COHERE_API_KEY=xxx` -> `{"X-Cohere-Api-Key": "xxx"}`
- Multiple keys set -> all headers present
- No keys -> empty dict
- **File**: `test_weaviate_client.py`

#### M6. `WeaviateClient._evolve_collection` with reranker
**Scenario**: Existing collection gets reranker config updated when `reranker_enabled=True`.
- **Verify**: `col.config.update(reranker_config=Reconfigure.Reranker.cohere())` called.
- **File**: `test_weaviate_client.py`

#### M7. `_build_prompt` truncation in `summarize.py`
**Scenario**: Properties with values > 500 chars get truncated in Flash prompt.
- **Setup**: Hit with a 1000-char property value.
- **Verify**: Prompt contains truncated version (500 chars).
- **File**: `test_knowledge_summarize.py`

#### M8. `@trace` decorator identity behavior when disabled
**Scenario**: `@trace(name="...")` returns the original function when tracing disabled.
- **Verify**: Decorated function is identical to undecorated function.
- **File**: `test_tracing.py` (partially covered, but not for the specific `func=None` branch)

#### M9. `knowledge_search` JSON string deserialization for collections param
**Scenario**: MCP JSON-RPC sends `collections` as a JSON string instead of a list.
- **Setup**: Call `knowledge_search(query="test", collections='["VideoAnalyses"]')`.
- **Verify**: Parsed correctly, search targets VideoAnalyses.
- **File**: `test_knowledge_tools.py`

#### M10. `knowledge_ingest` JSON string deserialization for properties param
**Scenario**: MCP JSON-RPC sends `properties` as a JSON string.
- **Setup**: Call `knowledge_ingest(collection="VideoAnalyses", properties='{"title": "Test"}')`.
- **Verify**: Parsed correctly, insert succeeds.
- **File**: `test_knowledge_tools.py`

### LOW Priority (Consistency and defensive checks)

#### L1. `_build_rerank` returns correct Weaviate Rerank object
**Scenario**: Unit test for the `_build_rerank` helper.
- **Verify**: Returns `Rerank(prop=prop, query=query)`.
- **File**: `test_knowledge_tools.py`

#### L2. `trace()` with `func=None` branch
**Scenario**: `@trace(name="x")` used as decorator factory (func is None, returns lambda).
- **Verify**: Returns identity lambda when disabled, returns `mlflow.trace(...)` when enabled.
- **File**: `test_tracing.py`

#### L3. `_is_env_placeholder` edge cases
**Scenario**: Various placeholder formats: `${VAR}`, `${VAR:-default}`, `$VAR`, non-placeholder.
- **Note**: Already implicitly tested via `_normalize_weaviate_url`, but direct unit tests would be cleaner.
- **File**: `test_config.py`

#### L4. `KnowledgeHit` model with rerank_score and summary fields
**Scenario**: Verify `KnowledgeHit` construction with new optional fields.
- **Verify**: Default `rerank_score=None`, `summary=None`. Fields serialize in `model_dump()`.
- **File**: `test_models.py`

#### L5. `KnowledgeSearchResult` model with reranked/flash_processed flags
**Scenario**: Verify new boolean fields default to `False` and serialize correctly.
- **File**: `test_models.py`

#### L6. `HitSummary` and `HitSummaryBatch` model validation
**Scenario**: Verify `relevance` field bounded `[0, 1]`, `useful_properties` defaults to empty list.
- **File**: `test_models.py`

---

## 5. Infrastructure Recommendations

### 5.1 Fixture Enhancement

The `mock_weaviate_client` fixture should support reranker-related query returns:

```python
# Add to conftest.py mock_weaviate_client fixture:
mock_obj = MagicMock()
mock_obj.properties = {"title": "Test", "summary": "Test summary"}
mock_obj.uuid = "test-uuid-1234"
mock_obj.metadata = MagicMock(
    score=0.85,
    distance=0.15,
    rerank_score=0.92,  # NEW: for reranker tests
)
mock_collection.query.hybrid.return_value = MagicMock(objects=[mock_obj])
mock_collection.query.near_text.return_value = MagicMock(objects=[mock_obj])
mock_collection.query.bm25.return_value = MagicMock(objects=[mock_obj])
```

### 5.2 Config Test Fixture

Add a parametrized fixture for testing `ServerConfig.from_env()` with various env combinations:

```python
@pytest.fixture()
def env_config(monkeypatch, clean_config):
    """Helper to build config from specific env vars."""
    def _set(**env_vars):
        for k, v in env_vars.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, str(v))
        import video_research_mcp.config as cfg_mod
        cfg_mod._config = None
        return cfg_mod.get_config()
    return _set
```

### 5.3 Test Organization

No new test files needed. All proposed tests fit naturally into existing test files:
- `test_config.py` — H5, H6, L3
- `test_knowledge_tools.py` — H1-H4, H7, M1-M3, M9-M10, L1
- `test_knowledge_agent_tools.py` — M4
- `test_knowledge_summarize.py` — M7
- `test_weaviate_client.py` — M5, M6
- `test_tracing.py` — M8, L2
- `test_models.py` — L4, L5, L6

### 5.4 Test Count Estimate

| Priority | Scenarios | Estimated Tests |
|----------|-----------|-----------------|
| HIGH | H1-H7 | ~20 tests |
| MEDIUM | M1-M10 | ~18 tests |
| LOW | L1-L6 | ~12 tests |
| **Total** | **23 scenarios** | **~50 new tests** |

This would bring the suite from 540 to ~590 tests.

---

## 6. Summary

**What's well-tested**: Core tool behavior, tracing lifecycle, Flash summarization in isolation, filter builder, YouTube download, context cache mechanics, QueryAgent agent tooling.

**Critical gaps**: The Cohere reranker integration in `knowledge_search` (the actual pipeline path from config -> query -> score extraction -> sorting) and the Flash summarization integration path in `search.py` have no tests. Config derivation for new fields (`reranker_enabled`, `flash_summarize`) is untested.

**Recommended order of implementation**: H1 -> H5 -> H2 -> H6 -> H3 -> H4 -> H7, then M-priority as time allows. This covers the highest-risk behavioral changes from PR #18 first.
