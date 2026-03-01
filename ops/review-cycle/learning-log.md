# Review Cycle Learning Log

## Iteration 1 (Architecture and Trust Boundaries) - 2026-03-01T03:26:51Z
- Observation: `content_analyze` accepted arbitrary URLs and passed them directly into Gemini `UrlContext` without applying the repo's SSRF policy gate.
- Inference: Trust boundary handling was inconsistent; URL hardening existed for document downloads (`url_policy.py`) but not for URL-context analysis.
- Strategy: Reuse `validate_url()` at tool ingress to unify outbound URL controls across tooling.
- Validation: Added guard in `content_analyze` and a regression test to assert non-HTTPS URLs are rejected pre-model-call.
- Confidence change: 0.55 -> 0.80 for URL-boundary consistency in content tooling after patch + test.
- Delivery confidence: 0.80 -> 0.88 after PR #30 merged cleanly into `codex/review-mainline`.

## Iteration 2 seed hypotheses
- Add an explicit per-tool trust policy matrix (local file, remote URL, external API) and test each edge.
- Evaluate whether `infra_*` mutating tools need an opt-in guard for non-local transports.

## Iteration 2 (Validation and Schema Contracts) - 2026-03-01T04:05:41Z
- Observation: Local filesystem inputs across multiple tools had no centralized boundary contract, while URL inputs already had shared policy controls.
- Inference: Validation strategy was asymmetric across trust boundaries, which increases policy drift risk and weakens schema-level ingress guarantees.
- Strategy: Introduce one shared local-path policy primitive and apply it at every local path ingress point.
- Validation: Added `LOCAL_FILE_ACCESS_ROOT` config, wired `enforce_local_access_root()` into all path-taking tool ingress points, and added focused regression tests.
- Confidence change: 0.42 -> 0.79 for local filesystem trust-boundary enforcement.
- Delivery confidence: 0.74 -> 0.82 after lint + targeted policy test pass.

## Iteration 3 seed hypotheses
- Validate external API failure categorization consistency (`make_tool_error`) under retries/timeouts.
- Add idempotency checks for partial-success batch/download flows.

## Iteration 3 (External API Failure Modes and Idempotency) - 2026-03-01T06:20:00Z
- Observation: Timeout/transport exceptions from async clients could bypass deterministic category mapping, and concurrent uploads with the same content hash could race before cache writes.
- Inference: Failure mode contracts depended on brittle string matching and non-atomic cache workflows, which weakens retry semantics and quota efficiency under concurrency.
- Strategy: Add typed network/timeout error categorization and introduce per-content-hash upload lock coordination in the File API upload path.
- Validation: Added regression tests for `make_tool_error()` timeout/network mappings and concurrent same-hash upload coalescing; focused lint/tests passed.
- Confidence change: 0.62 -> 0.82 for iteration-3 objective coverage.

## Iteration 4 seed hypotheses
- Review auth/capability guards for runtime-mutating tools (`infra_cache`, `infra_configure`).
- Audit secret propagation paths in logs and tool error payloads.
