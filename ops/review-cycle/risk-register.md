# Risk Register

## R-001
- Severity: High
- Area: Trust boundary / outbound fetch
- Evidence: Prior to iteration-1 patch, `content_analyze` accepted URL input and entered `_analyze_url` without `validate_url` guard.
- Current status: Mitigated in iteration 1 by adding URL policy validation at ingress.
- Residual risk: DNS-policy parity depends on continuous reuse of `validate_url()` by future URL-taking tools.

## R-002
- Severity: Medium
- Area: Operational integrity / authorization
- Evidence: Prior to iteration 4, `infra_cache(action="clear")` and mutating `infra_configure(...)` executed without explicit capability gating.
- Exploit reasoning: Any connected MCP client can modify global runtime behavior or erase cache state, creating integrity and availability impact.
- Status: Mitigated in iteration 4 via `INFRA_MUTATIONS_ENABLED` policy gate + optional `INFRA_ADMIN_TOKEN` enforcement.
- Residual risk: Deployments that intentionally set `INFRA_MUTATIONS_ENABLED=true` without a token still permit all connected clients to mutate config/cache.

## R-003
- Severity: Medium
- Area: Local filesystem trust boundary
- Evidence: Local path ingress previously resolved unrestricted host paths in video/content/document tools.
- Exploit reasoning: In shared or semi-trusted host setups, broad path access can expose sensitive local documents to LLM processing.
- Status: Mitigated in iteration 2 with `LOCAL_FILE_ACCESS_ROOT` policy gate; residual risk is misconfiguration when root is unset.

## R-004
- Severity: Medium
- Area: Validation/test contract reliability
- Evidence: Decorated tool direct calls fail as `FunctionTool` in subset test runs (`tests/test_content_tools.py`, `tests/test_content_batch_tools.py`).
- Exploit reasoning: Test harness contract drift can hide regressions and delay detection of real validation failures.
- Status: Open (schedule deep fix during iteration 9 regression blind-spot pass).

## R-005
- Severity: Medium
- Area: External API idempotency / quota integrity
- Evidence: Prior upload flow in `src/video_research_mcp/tools/video_file.py` had no same-hash lock around cache-check + upload critical section.
- Exploit reasoning: Concurrent retries could duplicate external uploads for the same content and amplify quota burn.
- Status: Mitigated in iteration 3 with per-content-hash upload lock and regression test.

## R-006
- Severity: Low
- Area: Partial-failure transparency / evidence integrity
- Evidence: `src/video_research_mcp/tools/research_document_file.py:109` and `:131` log and skip per-source failures without surfacing skipped sources in tool response.
- Exploit reasoning: Consumers may assume full-document coverage when synthesis actually used a subset, reducing trust in evidence completeness.
- Status: Open (patch-ready mitigation queued for iteration 6 fault-isolation pass).

## R-007
- Severity: High
- Area: Secret handling / control-plane disclosure
- Evidence: Prior to iteration 4, `infra_configure` returned `current_config` with non-Gemini credential fields still present (`youtube_api_key`, `weaviate_api_key`).
- Exploit reasoning: Any MCP client invoking infra config introspection could retrieve service credentials and pivot into external systems.
- Status: Mitigated in iteration 4 by redacting all secret-bearing config fields from infra responses.
