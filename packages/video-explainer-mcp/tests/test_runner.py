"""Tests for the subprocess runner."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from video_explainer_mcp.errors import SubprocessError
from video_explainer_mcp.runner import SubprocessResult, run_cli

pytestmark = pytest.mark.unit


class TestSubprocessResult:
    """Tests for the SubprocessResult dataclass."""

    def test_frozen(self):
        """SubprocessResult is immutable."""
        r = SubprocessResult("out", "err", 0, 1.5, ["cmd"])
        with pytest.raises(AttributeError):
            r.stdout = "new"

    def test_fields(self):
        """All fields are accessible."""
        r = SubprocessResult("out", "err", 0, 1.5, ["a", "b"])
        assert r.stdout == "out"
        assert r.stderr == "err"
        assert r.returncode == 0
        assert r.duration_seconds == 1.5
        assert r.command == ["a", "b"]


class TestRunCli:
    """Tests for run_cli function."""

    async def test_success(self, mock_subprocess, monkeypatch):
        """Successful CLI execution returns SubprocessResult."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake/path")
        proc = mock_subprocess(returncode=0, stdout=b"OK\n", stderr=b"")
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
            result = await run_cli("create", "test-project")
        assert result.stdout == "OK\n"
        assert result.returncode == 0

    async def test_failure_raises(self, mock_subprocess, monkeypatch):
        """Non-zero exit raises SubprocessError."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake/path")
        proc = mock_subprocess(returncode=1, stderr=b"Project not found: x")
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
            with pytest.raises(SubprocessError) as exc_info:
                await run_cli("status", "missing")
        assert exc_info.value.returncode == 1
        assert "Project not found" in exc_info.value.stderr

    async def test_timeout(self, monkeypatch):
        """Timeout sends SIGTERM then SIGKILL."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake/path")
        proc = AsyncMock()
        proc.returncode = -15
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.terminate = lambda: None
        proc.kill = lambda: None

        # After kill, communicate should return
        call_count = 0

        async def smart_communicate():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise asyncio.TimeoutError()
            return (b"", b"")

        proc.communicate = smart_communicate

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
            with pytest.raises(asyncio.TimeoutError):
                await run_cli("render", "slow-project", timeout=1)

    async def test_custom_cwd(self, mock_subprocess, monkeypatch):
        """Custom cwd is passed to subprocess."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake/path")
        proc = mock_subprocess(returncode=0, stdout=b"OK")
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)) as mock_exec:
            await run_cli("status", cwd="/custom/dir")
            call_kwargs = mock_exec.call_args
            assert call_kwargs.kwargs.get("cwd") == "/custom/dir"

    async def test_builds_correct_command(self, mock_subprocess, monkeypatch):
        """Command is built from config.explainer_python + args."""
        monkeypatch.setenv("EXPLAINER_PATH", "/fake/path")
        monkeypatch.setenv("EXPLAINER_PYTHON", "python3.12")
        proc = mock_subprocess(returncode=0, stdout=b"OK")
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)) as mock_exec:
            await run_cli("generate", "my-project", "--mock")
            args = mock_exec.call_args.args
            assert args[0] == "python3.12"
            assert args[1] == "-m"
            assert args[2] == "video_explainer"
            assert "generate" in args
            assert "my-project" in args
