---
paths: "**/*"
---

# Git — Project Overrides

Extends `~/.claude/rules/git.md`. Project-specific rules take precedence.

## Branch Protection

`main` is protected. Direct pushes are blocked; all changes go through PRs.

**Merging PRs**: use `--admin` to bypass protection rules (required status checks,
up-to-date branch requirement). This is intentional — you have owner privileges
on this repo.

```bash
gh pr merge <N> --squash --admin
```

If the PR branch is out of date AND the update would cause a conflict, resolve it
locally on the PR branch and force-push before merging:

```bash
gh pr update-branch <N>          # fast-path: no conflict
# or, if conflict:
gh pr checkout <N>
git fetch origin main && git merge origin/main
# resolve conflicts, then:
git push origin HEAD:<branch> --force
gh pr merge <N> --squash --admin
```

## Preferred Merge Strategy

Always `--squash` for feature PRs. Dependabot and chore PRs: `--squash` as well.
