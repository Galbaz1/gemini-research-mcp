"""Tests for video analysis prompt templates."""

from __future__ import annotations

from video_research_mcp.prompts.video import METADATA_OPTIMIZER, METADATA_PREAMBLE


class TestMetadataOptimizer:
    def test_formats_all_variables(self):
        """All template variables resolve without KeyError."""
        result = METADATA_OPTIMIZER.format(
            title="How to Build a CLI",
            channel="TechChannel",
            category="Science & Technology",
            duration="12:34",
            description_excerpt="In this video we build a CLI tool...",
            tags="python, cli, tutorial",
            instruction="Extract all commands shown",
        )
        assert "How to Build a CLI" in result
        assert "TechChannel" in result
        assert "Extract all commands shown" in result


class TestMetadataPreamble:
    def test_formats_all_variables(self):
        """All template variables resolve without KeyError."""
        result = METADATA_PREAMBLE.format(
            title="Cooking Pasta",
            channel="ChefTV",
            category="Howto & Style",
            duration="8:22",
            tags="pasta, italian, recipe",
        )
        assert '"Cooking Pasta"' in result
        assert "ChefTV" in result
        assert "8:22" in result
