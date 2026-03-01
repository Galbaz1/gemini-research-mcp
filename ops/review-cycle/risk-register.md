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
- Evidence: [`src/video_research_mcp/tools/infra.py:29`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/src/video_research_mcp/tools/infra.py:29) allows cache clear actions; [`src/video_research_mcp/tools/infra.py:65`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/src/video_research_mcp/tools/infra.py:65) allows runtime model reconfiguration with no explicit capability guard.
- Exploit reasoning: Any connected MCP client can modify global runtime behavior or erase cache state, creating integrity and availability impact.
- Status: Open (design mitigation queued).

## R-003
- Severity: Medium
- Area: Local filesystem trust boundary
- Evidence: [`src/video_research_mcp/tools/content_batch.py:61`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/src/video_research_mcp/tools/content_batch.py:61) and [`src/video_research_mcp/tools/content_batch.py:72`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/src/video_research_mcp/tools/content_batch.py:72) resolve user-supplied paths directly from host filesystem.
- Exploit reasoning: In shared or semi-trusted host setups, broad path access can expose sensitive local documents to LLM processing.
- Status: Open (needs policy decision on allowlisted roots).
