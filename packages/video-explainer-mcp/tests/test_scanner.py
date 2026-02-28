"""Tests for the project scanner."""

from __future__ import annotations

from video_explainer_mcp.scanner import (
    PIPELINE_STEPS,
    list_projects,
    project_exists,
    scan_project,
)


class TestScanProject:
    """Tests for scan_project."""

    async def test_nonexistent_project(self, monkeypatch, tmp_path):
        """Returns None for missing projects."""
        monkeypatch.setenv("EXPLAINER_PATH", str(tmp_path))
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(tmp_path / "projects"))
        (tmp_path / "projects").mkdir()
        result = await scan_project("nonexistent")
        assert result is None

    async def test_empty_project(self, monkeypatch, mock_project_dir):
        """Empty project shows all steps incomplete."""
        project = mock_project_dir(project_id="empty")
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        result = await scan_project("empty")
        assert result is not None
        assert result.project_id == "empty"
        assert all(not s.completed for s in result.steps)

    async def test_completed_steps(self, monkeypatch, mock_project_dir):
        """Detects completed steps correctly."""
        project = mock_project_dir(
            project_id="partial",
            completed_steps=["script", "narration"],
        )
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        result = await scan_project("partial")
        assert result is not None
        step_map = {s.name: s.completed for s in result.steps}
        assert step_map["script"] is True
        assert step_map["narration"] is True
        assert step_map["scenes"] is False

    async def test_all_steps_completed(self, monkeypatch, mock_project_dir):
        """Fully completed project."""
        project = mock_project_dir(
            project_id="full",
            completed_steps=PIPELINE_STEPS,
        )
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        result = await scan_project("full")
        assert result is not None
        assert all(s.completed for s in result.steps)

    async def test_has_render(self, monkeypatch, mock_project_dir):
        """Detects rendered output."""
        project = mock_project_dir(project_id="rendered")
        output_dir = project / "output"
        output_dir.mkdir()
        (output_dir / "video.mp4").write_text("")
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        result = await scan_project("rendered")
        assert result is not None
        assert result.has_render is True


class TestProjectExists:
    """Tests for project_exists."""

    def test_exists(self, monkeypatch, mock_project_dir):
        """Returns True for existing project."""
        project = mock_project_dir(project_id="exists")
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project.parent))
        assert project_exists("exists") is True

    def test_not_exists(self, monkeypatch, tmp_path):
        """Returns False for missing project."""
        projects = tmp_path / "projects"
        projects.mkdir()
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(projects))
        assert project_exists("nope") is False


class TestListProjects:
    """Tests for list_projects."""

    async def test_empty_dir(self, monkeypatch, tmp_path):
        """Returns empty list when no projects exist."""
        projects = tmp_path / "projects"
        projects.mkdir()
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(projects))
        result = await list_projects()
        assert result == []

    async def test_multiple_projects(self, monkeypatch, mock_project_dir):
        """Lists multiple projects with step counts."""
        mock_project_dir(project_id="alpha", completed_steps=["script"])
        project_b = mock_project_dir(project_id="beta", completed_steps=["script", "narration", "scenes"])
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(project_b.parent))
        result = await list_projects()
        assert len(result) == 2
        by_id = {p.project_id: p for p in result}
        assert by_id["alpha"].steps_completed == 1
        assert by_id["beta"].steps_completed == 3

    async def test_nonexistent_dir(self, monkeypatch, tmp_path):
        """Returns empty list when projects dir doesn't exist."""
        monkeypatch.setenv("EXPLAINER_PROJECTS_PATH", str(tmp_path / "nope"))
        result = await list_projects()
        assert result == []
