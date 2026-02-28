"""Tests for audio tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from video_explainer_mcp.tools.audio import explainer_music, explainer_sound


def _mock_result(stdout: str = "OK"):
    mock = AsyncMock()
    mock.stdout = stdout
    mock.stderr = ""
    mock.returncode = 0
    mock.duration_seconds = 1.0
    return mock


class TestExplainerSound:
    """Tests for explainer_sound tool."""

    async def test_analyze(self, monkeypatch):
        """Analyzes scenes for sound cues."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.audio.run_cli", return_value=_mock_result()) as mock_cli:
            result = await explainer_sound(project_id="test", action="analyze")
        assert result["action"] == "analyze"
        assert result["success"] is True
        assert "analyze" in mock_cli.call_args.args

    async def test_generate(self, monkeypatch):
        """Generates sound effects."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.audio.run_cli", return_value=_mock_result()):
            result = await explainer_sound(project_id="test", action="generate")
        assert result["success"] is True

    async def test_error(self, monkeypatch):
        """Returns tool error on failure."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        from video_explainer_mcp.errors import SubprocessError
        with patch(
            "video_explainer_mcp.tools.audio.run_cli",
            side_effect=SubprocessError(["cli"], 1, stderr="fail"),
        ):
            result = await explainer_sound(project_id="test", action="analyze")
        assert "error" in result


class TestExplainerMusic:
    """Tests for explainer_music tool."""

    async def test_generate_music(self, monkeypatch):
        """Generates background music."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.audio.run_cli", return_value=_mock_result()):
            result = await explainer_music(project_id="test")
        assert result["success"] is True
