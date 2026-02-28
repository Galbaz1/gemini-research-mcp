"""Quality gate checks for strict video contract pipeline.

Runs semantic validation, artifact existence, link integrity, and HTML
parseability checks. Returns a QualityReport with pass/fail status.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from ..models.video_contract import QualityCheck, QualityReport
from ..validation import validate_analysis

logger = logging.getLogger(__name__)


def run_quality_gates(
    analysis: dict,
    strategy: dict,
    concept_map: dict,
    artifact_dir: Path,
    *,
    coverage_min_ratio: float = 0.90,
    start_time: float,
) -> QualityReport:
    """Run all quality gates and return a QualityReport.

    Args:
        analysis: StrictVideoResult as dict.
        strategy: StrategyReport as dict.
        concept_map: ConceptMap as dict.
        artifact_dir: Directory containing rendered artifacts.
        coverage_min_ratio: Minimum video coverage ratio.
        start_time: Pipeline start time for duration calculation.

    Returns:
        QualityReport with all checks and overall status.
    """
    checks: list[QualityCheck] = []

    # Semantic validation
    duration = analysis.get("duration_seconds", 0)
    vr = validate_analysis(analysis, duration_seconds=duration, min_coverage=coverage_min_ratio)
    checks.append(QualityCheck(
        name="semantic_validation",
        passed=vr.passed,
        detail="; ".join(vr.issues) if vr.issues else "All semantic checks passed",
    ))

    # Artifact existence
    checks.append(_check_artifacts_exist(artifact_dir))

    # Link validity
    checks.append(_check_links_valid(artifact_dir))

    # HTML parseability
    checks.append(_check_html_parseable(artifact_dir))

    # Coverage ratio
    coverage_ratio = _compute_coverage_ratio(analysis)

    all_passed = all(c.passed for c in checks)
    elapsed = time.monotonic() - start_time

    return QualityReport(
        status="pass" if all_passed else "fail",
        coverage_ratio=coverage_ratio,
        checks=checks,
        duration_seconds=round(elapsed, 2),
    )


def _check_artifacts_exist(artifact_dir: Path) -> QualityCheck:
    """Verify that expected artifact files exist in the output directory."""
    expected = ["analysis.md", "strategy.md", "concept-map.html"]
    missing = [f for f in expected if not (artifact_dir / f).exists()]

    if missing:
        return QualityCheck(
            name="artifacts_exist",
            passed=False,
            detail=f"Missing artifacts: {', '.join(missing)}",
        )
    return QualityCheck(name="artifacts_exist", passed=True, detail="All artifacts present")


def _check_links_valid(artifact_dir: Path) -> QualityCheck:
    """Verify that relative links in markdown files resolve to existing files."""
    issues: list[str] = []
    link_pattern = re.compile(r"\[.*?\]\(([^)]+)\)")

    for md_file in artifact_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            link = match.group(1)
            if link.startswith(("http://", "https://", "#")):
                continue
            target = (md_file.parent / link).resolve()
            if not target.exists():
                issues.append(f"{md_file.name}: broken link '{link}'")

    if issues:
        return QualityCheck(
            name="links_valid",
            passed=False,
            detail="; ".join(issues),
        )
    return QualityCheck(name="links_valid", passed=True, detail="All relative links resolve")


def _check_html_parseable(artifact_dir: Path) -> QualityCheck:
    """Verify HTML files are well-formed (basic tag balance check)."""
    for html_file in artifact_dir.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        if "<html" not in content.lower() or "</html>" not in content.lower():
            return QualityCheck(
                name="html_parseable",
                passed=False,
                detail=f"{html_file.name}: missing <html> or </html> tags",
            )
    return QualityCheck(name="html_parseable", passed=True, detail="HTML files are well-formed")


def _compute_coverage_ratio(analysis: dict) -> float:
    """Compute the coverage ratio from timestamps and duration."""
    duration = analysis.get("duration_seconds", 0)
    if duration <= 0:
        return 1.0

    timestamps = analysis.get("timestamps", [])
    max_ts = 0
    for ts in timestamps:
        time_str = ts.get("time", "") if isinstance(ts, dict) else ""
        parts = time_str.split(":")
        try:
            seconds = sum(int(p) * (60 ** (len(parts) - 1 - j)) for j, p in enumerate(parts))
            max_ts = max(max_ts, seconds)
        except (ValueError, TypeError):
            continue

    return min(max_ts / duration, 1.0)
