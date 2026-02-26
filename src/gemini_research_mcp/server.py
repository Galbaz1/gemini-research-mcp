"""Main FastMCP server — mounts all sub-servers."""

from __future__ import annotations

from fastmcp import FastMCP

from .tools.video import video_server
from .tools.research import research_server
from .tools.content import content_server
from .tools.web import web_server
from .tools.infra import infra_server

app = FastMCP(
    "gemini-research",
    instructions=(
        "Unified Gemini research partner — video analysis, deep research, "
        "content extraction. Powered by Gemini 3.1 Pro with thinking support."
    ),
)

app.mount(video_server)
app.mount(research_server)
app.mount(content_server)
app.mount(web_server)
app.mount(infra_server)


def main() -> None:
    """Entry-point for ``gemini-research-mcp`` console script."""
    app.run()


if __name__ == "__main__":
    main()
