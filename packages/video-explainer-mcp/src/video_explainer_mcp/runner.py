"""Central subprocess executor for the video_explainer CLI."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from .config import get_config
from .errors import SubprocessError

logger = logging.getLogger(__name__)

SIGTERM_GRACE_SECONDS = 5


@dataclass(frozen=True)
class SubprocessResult:
    """Immutable result of a subprocess execution."""

    stdout: str
    stderr: str
    returncode: int
    duration_seconds: float
    command: list[str]


async def run_cli(
    *args: str,
    timeout: int | None = None,
    cwd: str | None = None,
) -> SubprocessResult:
    """Run the explainer CLI with the given arguments.

    Uses ``asyncio.create_subprocess_exec`` with an argument list (never
    shell=True) to prevent command injection. On timeout, sends SIGTERM,
    waits 5s, then SIGKILL.

    Args:
        *args: CLI arguments (e.g. ``"create"``, ``"my-project"``).
        timeout: Max seconds to wait. Defaults to ``config.timeout``.
        cwd: Working directory. Defaults to ``config.explainer_path``.

    Returns:
        SubprocessResult with stdout, stderr, returncode, duration.

    Raises:
        SubprocessError: On non-zero exit code.
        FileNotFoundError: When explainer CLI is not found.
        asyncio.TimeoutError: When process exceeds timeout.
    """
    cfg = get_config()
    if timeout is None:
        timeout = cfg.timeout
    if cwd is None:
        cwd = cfg.explainer_path or None

    cmd = [cfg.explainer_python, "-m", "video_explainer", *args]
    logger.info("Running: %s (timeout=%ds)", " ".join(cmd), timeout)
    start = time.monotonic()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Process timed out after %ds, sending SIGTERM", timeout)
        proc.terminate()
        try:
            await asyncio.wait_for(proc.communicate(), timeout=SIGTERM_GRACE_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("Process did not exit after SIGTERM, sending SIGKILL")
            proc.kill()
            await proc.communicate()
        raise

    elapsed = time.monotonic() - start
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    result = SubprocessResult(
        stdout=stdout,
        stderr=stderr,
        returncode=proc.returncode or 0,
        duration_seconds=round(elapsed, 2),
        command=cmd,
    )

    if result.returncode != 0:
        logger.error(
            "CLI failed (exit %d): %s\nstderr: %s",
            result.returncode,
            " ".join(cmd),
            stderr[:500],
        )
        raise SubprocessError(cmd, result.returncode, stdout, stderr)

    logger.info("CLI completed in %.1fs", elapsed)
    return result
