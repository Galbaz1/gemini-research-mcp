"""Main FastMCP server — mounts all sub-servers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from .client import GeminiClient
from .tools.video import video_server
from .tools.research import research_server
from .tools.content import content_server
from .tools.search import search_server
from .tools.infra import infra_server

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Startup/shutdown hook — tears down shared Gemini clients."""
    yield {}
    closed = await GeminiClient.close_all()
    logger.info("Lifespan shutdown: closed %d client(s)", closed)


app = FastMCP(
    "gemini-research",
    instructions=(
        "Unified Gemini research partner — video analysis, deep research, "
        "content extraction. Powered by Gemini 3.1 Pro with thinking support."
    ),
    lifespan=_lifespan,
)

app.mount(video_server)
app.mount(research_server)
app.mount(content_server)
app.mount(search_server)
app.mount(infra_server)


def main() -> None:
    """Entry-point for ``gemini-research-mcp`` console script."""
    app.run()


if __name__ == "__main__":
    main()
