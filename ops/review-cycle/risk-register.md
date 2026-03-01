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
- Evidence: [`src/video_research_mcp/tools/infra.py:29`](/Users/fausto/.codex/worktrees/1f67/gemini-research-mcp/src/video_research_mcp/tools/infra.py:29) allows cache clear actions; [`src/video_research_mcp/tools/infra.py:65`](/Users/fausto/.codex/worktrees/1f67/gemini-research-mcp/src/video_research_mcp/tools/infra.py:65) allows runtime model reconfiguration with no explicit capability guard.
- Exploit reasoning: Any connected MCP client can modify global runtime behavior or erase cache state, creating integrity and availability impact.
- Status: Open (design mitigation queued).

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
