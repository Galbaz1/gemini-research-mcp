# Security Fix Playbook

## FP-001: Enforce URL Policy at Tool Ingress
- Context: Any tool accepting user URLs and triggering outbound fetch behavior.
- Rule: Validate URL with `validate_url()` before model/tool fetch.
- Why: Prevents non-HTTPS, credentialed URLs, and private-network SSRF targets from crossing trust boundary.
- Applied in iteration 1:
  - [`src/video_research_mcp/tools/content.py`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/src/video_research_mcp/tools/content.py)
- Regression coverage:
  - [`tests/test_content_tools.py`](/Users/fausto/.codex/worktrees/ec3f/gemini-research-mcp/tests/test_content_tools.py)

## FP-002: Architectural Control Surface Review (queued)
- Context: Runtime-mutating tools (`infra_cache`, `infra_configure`) are callable without explicit auth gating.
- Candidate mitigation: Introduce optional capability gate via config/environment and reject mutating actions when disabled.
- Status: queued for design and compatibility analysis.

## FP-003: Constrain local file ingress with configurable root boundary
- Context: Tools accepting local file/directory paths in MCP environments.
- Rule: Resolve user path to absolute and enforce optional `LOCAL_FILE_ACCESS_ROOT` via shared helper before filesystem reads.
- Why: Reduces host filesystem exfiltration risk from induced tool calls in semi-trusted agent sessions.
- Applied in iteration 2:
  - `src/video_research_mcp/local_path_policy.py`
  - `src/video_research_mcp/tools/video_file.py`
  - `src/video_research_mcp/tools/content.py`
  - `src/video_research_mcp/tools/content_batch.py`
  - `src/video_research_mcp/tools/video_batch.py`
  - `src/video_research_mcp/tools/research_document_file.py`
- Regression coverage:
  - `tests/test_video_file.py`
  - `tests/test_content_tools.py`
  - `tests/test_content_batch_tools.py`
