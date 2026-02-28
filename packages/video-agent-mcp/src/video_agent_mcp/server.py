"""Main FastMCP server — mounts all sub-servers."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from .tools.scenes import scenes_server

logger = logging.getLogger(__name__)

app = FastMCP(
    "video-agent",
    instructions=(
        "Parallel scene generation for the video explainer pipeline. "
        "Uses Claude Agent SDK to run multiple scene generation prompts "
        "concurrently, reducing wall-clock time from ~21min to ~3-5min."
    ),
)

app.mount(scenes_server)


def main() -> None:
    """Entry-point for ``video-agent-mcp`` console script."""
    app.run()


if __name__ == "__main__":
    main()
