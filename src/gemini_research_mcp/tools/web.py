"""Web & search tools — 2 tools on a FastMCP sub-server."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from google.genai import types

from ..client import GeminiClient
from ..errors import make_tool_error
from ..prompts.content import WEB_ANALYZE

logger = logging.getLogger(__name__)
web_server = FastMCP("web")


@web_server.tool()
async def web_search(
    query: str,
    num_results: int = 5,
) -> dict:
    """Search the web using Gemini's built-in Google Search grounding.

    Returns relevant search results with title, URL, and snippet.
    """
    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        client = GeminiClient.get()
        from ..config import get_config

        cfg = get_config()
        response = await client.aio.models.generate_content(
            model=cfg.flash_model,
            contents=f"Search for: {query}\n\nReturn the top {num_results} most relevant results with title, URL, and a brief snippet for each.",
            config=config,
        )
        text = response.text or ""

        # Extract grounding metadata if available
        grounding = {}
        if response.candidates:
            cand = response.candidates[0]
            gm = getattr(cand, "grounding_metadata", None)
            if gm:
                chunks = getattr(gm, "grounding_chunks", []) or []
                grounding["sources"] = [
                    {
                        "title": getattr(getattr(c, "web", None), "title", ""),
                        "url": getattr(getattr(c, "web", None), "uri", ""),
                    }
                    for c in chunks
                ]

        return {"query": query, "response": text, **grounding}

    except Exception as exc:
        return make_tool_error(exc)


@web_server.tool()
async def web_analyze_url(
    url: str,
    prompt: str = "Summarize this page",
) -> dict:
    """Fetch and analyse a URL's content with a custom prompt."""
    try:
        content = types.Content(
            parts=[
                types.Part(file_data=types.FileData(file_uri=url)),
                types.Part(text=WEB_ANALYZE.format(prompt=prompt)),
            ]
        )
        resp = await GeminiClient.generate(content, thinking_level="medium")
        return {"url": url, "content": resp}
    except Exception as exc:
        return make_tool_error(exc)
