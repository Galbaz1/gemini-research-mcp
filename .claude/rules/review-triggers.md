---
paths: "**/*"
---

# Code Review Trigger Protocol

Use `scripts/detect_review_scope.py --json` before any review/audit request.

## Trigger Conditions

- Trigger review-scope detection when the user asks to review, audit, validate changes, check regressions, or assess merge readiness.
- Trigger again after substantial git-state transitions (new commits, rebase, stash apply, merge, or branch switch).

## Scope Selection

- `mode=uncommitted`: run a local-diff review against working tree changes.
  - Focus on correctness, edge cases, obvious security/perf regressions, and missing tests in touched code.
- `mode=commits`: review commit range `base_branch..HEAD`.
  - Focus on per-commit intent, behavioral regressions across commits, and commit-to-test coverage.
- `mode=pr`: run PR-context review.
  - Focus on merge readiness, cross-file integration, required changes vs suggestions, and clear final verdict.
- `mode=none`: report that there is nothing reviewable in current git scope.

## Priority Rules

Apply scopes in this order when multiple are technically possible:
1. `uncommitted`
2. `pr`
3. `commits`

Do not mix feedback scopes in one pass unless the user explicitly asks for combined output.
