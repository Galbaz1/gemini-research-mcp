"""Tests for project management tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from video_explainer_mcp.tools.project import (
    explainer_create,
    explainer_inject,
    explainer_list,
    explainer_status,
)

pytestmark = pytest.mark.unit


class TestExplainerCreate:
    """Tests for explainer_create tool."""

    async def test_not_configured(self, monkeypatch):
        """Returns error when EXPLAINER_PATH is not set."""
        monkeypatch.delenv("EXPLAINER_PATH", raising=False)
        result = await explainer_create(project_id="test")
        assert "error" in result

    async def test_success(self, monkeypatch, tmp_path):
        """Creates project via CLI."""
        explainer_dir = tmp_path / "explainer"
        explainer_dir.mkdir()
        projects_dir = explainer_dir / "projects"
        projects_dir.mkdir()
        monkeypatch.setenv("EXPLAINER_PATH", str(explainer_dir))

        mock_result = AsyncMock()
        mock_result.stdout = "Project created"
        mock_result.duration_seconds = 0.5
        with patch("video_explainer_mcp.tools.project.run_cli", return_value=mock_result):
            result = await explainer_create(project_id="my-video")
        assert result["project_id"] == "my-video"
        assert "created" in result["message"].lower()

    async def test_cli_error(self, monkeypatch, tmp_path):
        """Returns tool error on CLI failure."""
        explainer_dir = tmp_path / "explainer"
        explainer_dir.mkdir()
        monkeypatch.setenv("EXPLAINER_PATH", str(explainer_dir))

        from video_explainer_mcp.errors import SubprocessError
        with patch(
            "video_explainer_mcp.tools.project.run_cli",
            side_effect=SubprocessError(["cli"], 1, stderr="already exists"),
        ):
            result = await explainer_create(project_id="dup")
        assert "error" in result


class TestExplainerInject:
    """Tests for explainer_inject tool."""

    async def test_inject_content(self, monkeypatch, mock_project_dir):
        """Writes content to input/ directory."""
        project = mock_project_dir(project_id="inject-test")
        monkeypatch.setenv("EXPLAINER_PATH", str(project.parent.parent))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))

        result = await explainer_inject(
            project_id="inject-test",
            content="# My Research\n\nFindings here.",
            filename="research.md",
        )
        assert "files_written" in result
        assert len(result["files_written"]) == 1
        assert (project / "input" / "research.md").exists()

    async def test_project_not_found(self, monkeypatch, tmp_path):
        """Returns error for missing project."""
        projects = tmp_path / "projects"
        projects.mkdir()
        monkeypatch.setenv("EXPLAINER_PATH", str(tmp_path))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(projects))
        result = await explainer_inject(
            project_id="missing",
            content="test",
        )
        assert "error" in result


class TestExplainerStatus:
    """Tests for explainer_status tool."""

    async def test_existing_project(self, monkeypatch, mock_project_dir):
        """Returns step completion for existing project."""
        project = mock_project_dir(
            project_id="status-test",
            completed_steps=["script", "narration"],
        )
        monkeypatch.setenv("EXPLAINER_PATH", str(project.parent.parent))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        result = await explainer_status(project_id="status-test")
        assert result["project_id"] == "status-test"
        assert len(result["steps"]) == 5

    async def test_missing_project(self, monkeypatch, tmp_path):
        """Returns error for missing project."""
        projects = tmp_path / "projects"
        projects.mkdir()
        monkeypatch.setenv("EXPLAINER_PATH", str(tmp_path))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(projects))
        result = await explainer_status(project_id="nope")
        assert "error" in result

    async def test_not_configured(self, monkeypatch):
        """Returns error when EXPLAINER_PATH is not set."""
        monkeypatch.delenv("EXPLAINER_PATH", raising=False)
        result = await explainer_status(project_id="test")
        assert "error" in result


class TestExplainerList:
    """Tests for explainer_list tool."""

    async def test_list_projects(self, monkeypatch, mock_project_dir):
        """Lists projects with counts."""
        mock_project_dir(project_id="alpha", completed_steps=["script"])
        project_b = mock_project_dir(project_id="beta")
        monkeypatch.setenv("EXPLAINER_PATH", str(project_b.parent.parent))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project_b.parent))
        result = await explainer_list()
        assert result["total"] == 2

    async def test_not_configured(self, monkeypatch):
        """Returns error when not configured."""
        monkeypatch.delenv("EXPLAINER_PATH", raising=False)
        result = await explainer_list()
        assert "error" in result
