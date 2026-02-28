"""Semantic validation for video analysis results.

Checks that go beyond schema conformance: timestamp ordering,
key-point substance, concept-map referential integrity, and
video coverage ratio. Used by the strict pipeline's quality gates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Aggregated result of all validation checks."""

    passed: bool
    issues: list[str] = field(default_factory=list)


def validate_timestamps(timestamps: list[dict]) -> list[str]:
    """Check timestamp ordering and format.

    Returns:
        List of issue strings (empty = all valid).
    """
    issues: list[str] = []
    prev_seconds = -1

    for i, ts in enumerate(timestamps):
        time_str = ts.get("time", "")
        if not re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", time_str):
            issues.append(f"Timestamp {i}: invalid format '{time_str}'")
            continue

        parts = time_str.split(":")
        seconds = sum(int(p) * (60 ** (len(parts) - 1 - j)) for j, p in enumerate(parts))

        if seconds < prev_seconds:
            issues.append(
                f"Timestamp {i}: '{time_str}' is out of order (before previous)"
            )
        prev_seconds = seconds

    return issues


def validate_key_points(key_points: list[str], *, min_length: int = 20) -> list[str]:
    """Check that key points have minimum substance.

    Returns:
        List of issue strings for points that are too short.
    """
    issues: list[str] = []
    for i, point in enumerate(key_points):
        if len(point.strip()) < min_length:
            issues.append(
                f"Key point {i}: too short ({len(point.strip())} chars, min {min_length})"
            )
    return issues


def validate_concept_edges(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Check that all edge endpoints reference existing nodes.

    Returns:
        List of issue strings for dangling references.
    """
    node_ids = {n.get("id") for n in nodes}
    issues: list[str] = []

    for i, edge in enumerate(edges):
        if edge.get("source") not in node_ids:
            issues.append(f"Edge {i}: source '{edge.get('source')}' not in nodes")
        if edge.get("target") not in node_ids:
            issues.append(f"Edge {i}: target '{edge.get('target')}' not in nodes")

    return issues


def validate_coverage(
    timestamps: list[dict],
    duration_seconds: int,
    *,
    min_ratio: float = 0.90,
) -> list[str]:
    """Check that timestamps cover enough of the video duration.

    Skips check when duration_seconds <= 0 (live streams, unknown duration).

    Returns:
        List of issue strings if coverage is below threshold.
    """
    if duration_seconds <= 0 or not timestamps:
        return []

    max_ts = 0
    for ts in timestamps:
        time_str = ts.get("time", "")
        parts = time_str.split(":")
        try:
            seconds = sum(int(p) * (60 ** (len(parts) - 1 - j)) for j, p in enumerate(parts))
            max_ts = max(max_ts, seconds)
        except (ValueError, TypeError):
            continue

    ratio = max_ts / duration_seconds if duration_seconds > 0 else 0
    if ratio < min_ratio:
        return [
            f"Coverage {ratio:.0%} is below minimum {min_ratio:.0%} "
            f"(last timestamp at {max_ts}s of {duration_seconds}s)"
        ]
    return []


def validate_analysis(
    result: dict,
    *,
    duration_seconds: int = 0,
    min_coverage: float = 0.90,
) -> ValidationResult:
    """Run all semantic validations on a video analysis result.

    Args:
        result: Dict with timestamps, key_points, etc.
        duration_seconds: Video duration (0 = skip coverage check).
        min_coverage: Minimum coverage ratio for quality gate.

    Returns:
        ValidationResult with passed flag and collected issues.
    """
    issues: list[str] = []

    timestamps = result.get("timestamps", [])
    if isinstance(timestamps, list):
        ts_dicts = [
            t if isinstance(t, dict) else t.model_dump() if hasattr(t, "model_dump") else {}
            for t in timestamps
        ]
        issues.extend(validate_timestamps(ts_dicts))
        issues.extend(validate_coverage(ts_dicts, duration_seconds, min_ratio=min_coverage))

    key_points = result.get("key_points", [])
    if isinstance(key_points, list):
        issues.extend(validate_key_points(key_points))

    return ValidationResult(passed=len(issues) == 0, issues=issues)
