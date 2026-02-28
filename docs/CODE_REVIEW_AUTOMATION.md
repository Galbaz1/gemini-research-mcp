# Code Review Automation Triggers

This repository includes a deterministic trigger mechanism for selecting the right review scope in Claude Code sessions, including sessions outside this chat.

## Components

- `scripts/detect_review_scope.py` — reads git + optional GitHub CLI state and returns one mode:
  - `uncommitted`
  - `pr`
  - `commits`
  - `none`
- `.claude/rules/review-triggers.md` — instructs Claude Code when to run detection and how to map each mode to a review workflow.

## Decision Logic

Priority order:
1. `uncommitted`
2. `pr`
3. `commits`
4. `none`

Detailed checks:

1. Uncommitted changes
   - Signal: `git status --porcelain` has lines.
   - Result: `mode=uncommitted`.

2. Pull Request context
   - Signal: no uncommitted changes and `gh pr view` returns an open PR.
   - Result: `mode=pr`.
   - If `gh` is unavailable or unauthenticated, this check is skipped safely.

3. Existing commits (branch-level)
   - Signal: no uncommitted changes, no open PR, `git rev-list --count <base>..HEAD > 0`.
   - Result: `mode=commits`.

4. No reviewable scope
   - Signal: none of the above.
   - Result: `mode=none`.

Base branch selection:
- First choice: `origin/HEAD` symbolic ref.
- Fallback: `main`, then `master`, else `main`.

## Usage

Human-readable:

```bash
scripts/detect_review_scope.py
```

Machine-readable:

```bash
scripts/detect_review_scope.py --json
```

Example JSON:

```json
{
  "mode": "commits",
  "reason": "Branch is ahead of base with no local unstaged/uncommitted files.",
  "branch": "feature/cache-bridge",
  "base_branch": "main",
  "uncommitted_files": 0,
  "ahead_commits": 3,
  "pr_context": false,
  "pr_url": null
}
```

## Claude Code Session Scenario (outside this conversation)

Typical flow in a fresh Claude Code session:

1. User asks: "Review my changes."
2. Agent runs `scripts/detect_review_scope.py --json`.
3. If output is:
   - `uncommitted`: review only current working-tree diff.
   - `commits`: review commit range against base branch.
   - `pr`: review in merge-readiness framing with required changes vs suggestions.
4. Agent reruns detection after major git transitions before a second review pass.

This keeps review feedback aligned with current repository state and prevents scope mixing.
