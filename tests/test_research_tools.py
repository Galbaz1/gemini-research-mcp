"""Tests for research tool helpers."""

from __future__ import annotations

from gemini_research_mcp.tools.research import _parse_findings


class TestParseFindings:
    def test_parse_single_finding(self):
        text = "[CONFIRMED] Climate change is accelerating.\nSupporting: IPCC 2024 report"
        findings = _parse_findings(text)
        assert len(findings) == 1
        assert findings[0].evidence_tier == "CONFIRMED"
        assert "Climate change" in findings[0].claim

    def test_parse_multiple_findings(self):
        text = """[CONFIRMED] Fact A is true.
Supporting: Source 1
[SPECULATION] Fact B might be true.
[INFERENCE] Fact C follows from A."""
        findings = _parse_findings(text)
        assert len(findings) == 3
        assert findings[0].evidence_tier == "CONFIRMED"
        assert findings[1].evidence_tier == "SPECULATION"
        assert findings[2].evidence_tier == "INFERENCE"

    def test_parse_empty(self):
        assert _parse_findings("No findings here") == []

    def test_parse_strong_indicator(self):
        text = "[STRONG INDICATOR] This pattern is consistent."
        findings = _parse_findings(text)
        assert len(findings) == 1
        assert findings[0].evidence_tier == "STRONG INDICATOR"
