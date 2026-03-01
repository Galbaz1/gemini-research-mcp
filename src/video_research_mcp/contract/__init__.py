"""Strict video output contract pipeline — opt-in quality enforcement.

Public API:
    run_strict_pipeline() — the main entry point called by video_analyze
    when strict_contract=True.
"""

from .pipeline import run_strict_pipeline

__all__ = ["run_strict_pipeline"]
