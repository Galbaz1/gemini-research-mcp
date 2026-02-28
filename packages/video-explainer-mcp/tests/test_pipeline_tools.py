"""Tests for pipeline execution tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from video_explainer_mcp.jobs import clear_jobs
from video_explainer_mcp.tools.pipeline import (
    explainer_generate,
    explainer_render,
    explainer_render_poll,
    explainer_short,
    explainer_step,
)


@pytest.fixture(autouse=True)
def _clean_jobs_for_pipeline():
    clear_jobs()
    yield
    clear_jobs()


def _mock_cli_result(stdout: str = "OK", duration: float = 1.0):
    """Create a mock SubprocessResult."""
    mock = AsyncMock()
    mock.stdout = stdout
    mock.stderr = ""
    mock.returncode = 0
    mock.duration_seconds = duration
    return mock


class TestExplainerGenerate:
    """Tests for explainer_generate tool."""

    async def test_full_pipeline(self, monkeypatch):
        """Runs full pipeline with mock TTS."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()):
            result = await explainer_generate(project_id="test")
        assert result["success"] is True

    async def test_partial_pipeline(self, monkeypatch):
        """Runs from/to subset."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()) as mock_cli:
            result = await explainer_generate(
                project_id="test", from_step="narration", to_step="scenes"
            )
        assert result["success"] is True
        call_args = mock_cli.call_args.args
        assert "--from" in call_args
        assert "narration" in call_args

    async def test_force_flag(self, monkeypatch):
        """Passes --force when requested."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()) as mock_cli:
            await explainer_generate(project_id="test", force=True)
        assert "--force" in mock_cli.call_args.args

    async def test_error_handling(self, monkeypatch):
        """Returns tool error on failure."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        from video_explainer_mcp.errors import SubprocessError
        with patch(
            "video_explainer_mcp.tools.pipeline.run_cli",
            side_effect=SubprocessError(["cli"], 1, stderr="Step failed"),
        ):
            result = await explainer_generate(project_id="fail")
        assert "error" in result


class TestExplainerStep:
    """Tests for explainer_step tool."""

    async def test_single_step(self, monkeypatch):
        """Runs a single step."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()):
            result = await explainer_step(project_id="test", step="script")
        assert result["step"] == "script"
        assert result["success"] is True

    async def test_tts_provider_args(self, monkeypatch):
        """Passes TTS provider from config."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        monkeypatch.setenv("EXPLAINER_TTS_PROVIDER", "elevenlabs")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()) as mock_cli:
            await explainer_step(project_id="test", step="voiceover")
        call_args = mock_cli.call_args.args
        assert "--tts-provider" in call_args
        assert "elevenlabs" in call_args


class TestExplainerRender:
    """Tests for explainer_render tool."""

    async def test_blocking_render(self, monkeypatch, tmp_path):
        """Blocking render completes and finds output."""
        projects = tmp_path / "projects"
        project = projects / "test"
        output = project / "output"
        output.mkdir(parents=True)
        (output / "video.mp4").write_text("")
        monkeypatch.setenv("EXPLAINER_PATH", str(tmp_path))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(projects))

        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()):
            result = await explainer_render(project_id="test", resolution="1080p")
        assert result["success"] is True
        assert result["output_file"].endswith(".mp4")

    async def test_fast_flag(self, monkeypatch):
        """Passes --fast by default."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()) as mock_cli:
            await explainer_render(project_id="test")
        assert "--fast" in mock_cli.call_args.args


class TestExplainerRenderPoll:
    """Tests for background render polling."""

    async def test_poll_missing_job(self):
        """Returns error for unknown job ID."""
        result = await explainer_render_poll(job_id="nonexistent")
        assert "error" in result

    async def test_poll_existing_job(self):
        """Returns job status."""
        from video_explainer_mcp.jobs import create_job, update_job, JobStatus
        job = create_job("test")
        update_job(job.job_id, status=JobStatus.COMPLETED, output_file="/out.mp4")
        result = await explainer_render_poll(job_id=job.job_id)
        assert result["status"] == "completed"
        assert result["output_file"] == "/out.mp4"


class TestExplainerShort:
    """Tests for shorts generation."""

    async def test_generate_short(self, monkeypatch):
        """Generates a short video."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake")
        with patch("video_explainer_mcp.tools.pipeline.run_cli", return_value=_mock_cli_result()):
            result = await explainer_short(project_id="test")
        assert result["success"] is True
