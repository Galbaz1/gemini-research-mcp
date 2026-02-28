#!/usr/bin/env python3
"""Detect which code-review scope should run based on git repository state."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ReviewScope:
    """Normalized review scope decision for automation."""

    mode: str
    reason: str
    branch: str
    base_branch: str
    uncommitted_files: int
    ahead_commits: int
    pr_context: bool
    pr_url: str | None


def _run_git(*args: str) -> str:
    """Run a git command and return stripped stdout or empty string on failure."""
    try:
        proc = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _run_cmd(*args: str) -> tuple[int, str]:
    """Run a command and return (exit_code, stdout)."""
    try:
        proc = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return (127, "")
    return (proc.returncode, proc.stdout.strip())


def _default_base_branch() -> str:
    """Infer merge base branch with sane fallbacks."""
    remote_head = _run_git("symbolic-ref", "refs/remotes/origin/HEAD")
    if remote_head.startswith("refs/remotes/origin/"):
        return remote_head.rsplit("/", 1)[-1]

    local_branches = _run_git("for-each-ref", "--format=%(refname:short)", "refs/heads")
    names = set(local_branches.splitlines()) if local_branches else set()
    if "main" in names:
        return "main"
    if "master" in names:
        return "master"
    return "main"


def _open_pr_context() -> tuple[bool, str | None]:
    """Detect open pull-request context with GitHub CLI if available."""
    if shutil.which("gh") is None:
        return (False, None)

    auth_code, _ = _run_cmd("gh", "auth", "status")
    if auth_code != 0:
        return (False, None)

    code, out = _run_cmd(
        "gh",
        "pr",
        "view",
        "--json",
        "url,state",
        "--jq",
        'select(.state == "OPEN") | .url',
    )
    if code != 0 or not out:
        return (False, None)
    return (True, out)


def detect_scope() -> ReviewScope:
    """Compute review scope based on working tree, branch, and PR state."""
    inside_repo = _run_git("rev-parse", "--is-inside-work-tree")
    if inside_repo != "true":
        return ReviewScope(
            mode="none",
            reason="Not inside a git repository.",
            branch="",
            base_branch="main",
            uncommitted_files=0,
            ahead_commits=0,
            pr_context=False,
            pr_url=None,
        )

    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
    base_branch = _default_base_branch()
    status_lines = _run_git("status", "--porcelain")
    uncommitted_files = len([line for line in status_lines.splitlines() if line.strip()])

    rev_range = f"{base_branch}..HEAD"
    ahead_raw = _run_git("rev-list", "--count", rev_range)
    ahead_commits = int(ahead_raw) if ahead_raw.isdigit() else 0

    pr_context, pr_url = _open_pr_context()

    if uncommitted_files > 0:
        return ReviewScope(
            mode="uncommitted",
            reason="Working tree has local changes.",
            branch=branch,
            base_branch=base_branch,
            uncommitted_files=uncommitted_files,
            ahead_commits=ahead_commits,
            pr_context=pr_context,
            pr_url=pr_url,
        )

    if pr_context:
        return ReviewScope(
            mode="pr",
            reason="Branch has an open pull request.",
            branch=branch,
            base_branch=base_branch,
            uncommitted_files=uncommitted_files,
            ahead_commits=ahead_commits,
            pr_context=pr_context,
            pr_url=pr_url,
        )

    if ahead_commits > 0:
        return ReviewScope(
            mode="commits",
            reason="Branch is ahead of base with no local unstaged/uncommitted files.",
            branch=branch,
            base_branch=base_branch,
            uncommitted_files=uncommitted_files,
            ahead_commits=ahead_commits,
            pr_context=pr_context,
            pr_url=pr_url,
        )

    return ReviewScope(
        mode="none",
        reason="No local changes and no ahead commits to review.",
        branch=branch,
        base_branch=base_branch,
        uncommitted_files=uncommitted_files,
        ahead_commits=ahead_commits,
        pr_context=pr_context,
        pr_url=pr_url,
    )


def _print_human(scope: ReviewScope) -> None:
    print(f"mode={scope.mode}")
    print(f"reason={scope.reason}")
    print(f"branch={scope.branch}")
    print(f"base_branch={scope.base_branch}")
    print(f"uncommitted_files={scope.uncommitted_files}")
    print(f"ahead_commits={scope.ahead_commits}")
    print(f"pr_context={'yes' if scope.pr_context else 'no'}")
    if scope.pr_url:
        print(f"pr_url={scope.pr_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    args = parser.parse_args()

    scope = detect_scope()
    if args.json:
        print(json.dumps(asdict(scope), ensure_ascii=True))
        return 0

    _print_human(scope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
