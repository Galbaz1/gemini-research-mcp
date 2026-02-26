"""Content analysis tools — 3 tools on a FastMCP sub-server."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastmcp import FastMCP
from google.genai import types

from ..client import GeminiClient
from ..errors import make_tool_error
from ..models.content import DocumentAnalysis, Summary
from ..prompts.content import ANALYZE_DOCUMENT, STRUCTURED_EXTRACT, SUMMARIZE

logger = logging.getLogger(__name__)
content_server = FastMCP("content")


def _build_content_parts(
    *,
    file_path: str | None = None,
    url: str | None = None,
    text: str | None = None,
) -> tuple[list[types.Part], str]:
    """Build Gemini parts from the first non-None content source.

    Returns (parts, description) for prompt interpolation.
    """
    parts: list[types.Part] = []
    description = ""

    if file_path:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        mime = "application/pdf" if p.suffix.lower() == ".pdf" else "text/plain"
        data = p.read_bytes()
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        description = f"Document: {p.name}"
    elif url:
        parts.append(types.Part(file_data=types.FileData(file_uri=url)))
        description = f"Content at URL: {url}"
    elif text:
        parts.append(types.Part(text=text))
        description = "Provided text content"
    else:
        raise ValueError("Provide at least one of: file_path, url, or text")

    return parts, description


@content_server.tool()
async def content_analyze_document(
    file_path: str | None = None,
    url: str | None = None,
    text: str | None = None,
    focus: str = "",
    thinking_level: str = "medium",
) -> dict:
    """Analyse a document (PDF, text, or URL) — summary, key points, entities.

    Uses Gemini's native PDF understanding for file_path inputs.
    """
    try:
        parts, desc = _build_content_parts(file_path=file_path, url=url, text=text)
    except (FileNotFoundError, ValueError) as exc:
        return make_tool_error(exc)

    focus_instruction = f"Focus your analysis on: {focus}" if focus else ""
    prompt_text = ANALYZE_DOCUMENT.format(
        content_description=desc, focus_instruction=focus_instruction
    )
    parts.append(types.Part(text=prompt_text))

    try:
        resp = await GeminiClient.generate(
            types.Content(parts=parts),
            thinking_level=thinking_level,
        )

        # Best-effort parse
        lines = resp.split("\n")
        summary = ""
        key_points: list[str] = []
        entities: list[str] = []
        quality = ""
        methodology = ""
        structure = ""
        section = ""

        for ln in lines:
            s = ln.strip()
            up = s.upper()
            if "SUMMARY" in up and (":" in up or up.startswith("#")):
                section = "summary"
                continue
            if "KEY POINT" in up:
                section = "kp"
                continue
            if "STRUCTURE" in up:
                section = "struct"
                continue
            if "ENTIT" in up:
                section = "ent"
                continue
            if "METHODOLOGY" in up:
                section = "meth"
                continue
            if "QUALITY" in up:
                section = "qual"
                continue

            if section == "summary" and s:
                summary += s + " "
            elif section == "kp" and s.startswith("-"):
                key_points.append(s.lstrip("- "))
            elif section == "struct" and s:
                structure += s + " "
            elif section == "ent" and s.startswith("-"):
                entities.append(s.lstrip("- "))
            elif section == "meth" and s:
                methodology += s + " "
            elif section == "qual" and s:
                quality += s + " "

        return DocumentAnalysis(
            summary=summary.strip() or resp[:500],
            key_points=key_points,
            structure=structure.strip(),
            entities=entities,
            methodology_notes=methodology.strip(),
            quality_assessment=quality.strip(),
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@content_server.tool()
async def content_summarize(
    content: str,
    detail_level: str = "medium",
) -> dict:
    """Summarize content at brief / medium / detailed level."""
    prompt = SUMMARIZE.format(content=content, detail_level=detail_level)
    try:
        resp = await GeminiClient.generate(prompt, thinking_level="low")

        # Parse TEXT: and KEY_TAKEAWAYS:
        text = ""
        takeaways: list[str] = []
        in_text = False
        for ln in resp.split("\n"):
            s = ln.strip()
            if s.upper().startswith("TEXT:"):
                text = s[5:].strip()
                in_text = True
                continue
            if s.upper().startswith("KEY_TAKEAWAYS:") or s.upper().startswith("KEY TAKEAWAYS:"):
                in_text = False
                items = s.split(":", 1)[1].strip()
                takeaways = [i.strip() for i in items.split("|") if i.strip()]
                continue
            if in_text and s:
                text += " " + s

        return Summary(
            text=text.strip() or resp,
            word_count=len((text or resp).split()),
            key_takeaways=takeaways,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@content_server.tool()
async def content_structured_extract(
    content: str,
    schema: dict,
) -> dict:
    """Extract structured data from content using a JSON Schema.

    Uses Gemini's ``response_json_schema`` for guaranteed structured output.
    """
    try:
        prompt = STRUCTURED_EXTRACT.format(
            content=content,
            schema_description=json.dumps(schema, indent=2),
        )
        resp = await GeminiClient.generate(
            prompt,
            thinking_level="low",
            response_schema=schema,
        )
        return json.loads(resp)
    except json.JSONDecodeError:
        return {"raw_response": resp, "error": "Failed to parse JSON from model response"}
    except Exception as exc:
        return make_tool_error(exc)
