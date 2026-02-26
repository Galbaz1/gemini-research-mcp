"""Video analysis tools — 5 tools on a FastMCP sub-server."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import parse_qs, urlparse

from fastmcp import FastMCP
from google.genai import types

from ..cache import load as cache_load, save as cache_save
from ..client import GeminiClient
from ..config import get_config
from ..errors import make_tool_error
from ..models.video import ComparisonResult, SessionInfo, SessionResponse, VideoAnalysis
from ..prompts.video import COMPARISON_TEMPLATE, PROMPTS, TRANSCRIPT_EXTRACT
from ..sessions import session_store

logger = logging.getLogger(__name__)
video_server = FastMCP("video")

# ── URL helpers ───────────────────────────────────────────────────────────────


def _normalize_youtube_url(url: str) -> str:
    """Normalize to ``https://www.youtube.com/watch?v=VIDEO_ID``."""
    url = url.replace("\\", "")
    parsed = urlparse(url)
    video_id: str | None = None
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    video_id = video_id.split("&")[0].split("?")[0]
    return f"https://www.youtube.com/watch?v={video_id}"


def _extract_video_id(url: str) -> str:
    url = url.replace("\\", "")
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        vid = parse_qs(parsed.query).get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        vid = parsed.path.strip("/")
    else:
        raise ValueError(f"Not a YouTube URL: {url}")
    if not vid:
        raise ValueError(f"Could not extract video ID from: {url}")
    return vid.split("&")[0].split("?")[0]


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_labeled_line(response: str, label: str) -> str:
    pattern = rf"\*?\*?{label}\*?\*?\s*:?\s*(.+?)(?=\n[A-Z]+\s*:|$)"
    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\*+", "", match.group(1)).strip().rstrip()
    return ""


def _parse_list_from_label(response: str, label: str) -> list[str]:
    content = _parse_labeled_line(response, label)
    if not content:
        return []
    sep = "|" if "|" in content else ","
    return [i.strip() for i in content.split(sep) if i.strip() and len(i.strip()) > 2]


def _parse_markdown_section(response: str, section: str) -> list[str]:
    pattern = (
        rf"(?:###?\s*\*?\*?{section}\*?\*?|^\*?\*?{section}\*?\*?\s*$)"
        rf"(.*?)(?=###|\*\*[A-Z]|\Z)"
    )
    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    if not match:
        return []
    items: list[str] = []
    for line in match.group(1).strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"`([^`]+)`\s*[|\-]?\s*(.*)", line)
        if m:
            item, desc = m.group(1).strip(), m.group(2).strip()
            items.append(f"`{item}`: {desc}" if desc else f"`{item}`")
        elif "|" in line:
            parts = line.split("|", 1)
            item = parts[0].strip().strip("`")
            desc = parts[1].strip() if len(parts) > 1 else ""
            if item and len(item) > 2:
                items.append(f"`{item}`: {desc}" if desc else f"`{item}`")
    return items


# ── Internal helpers ──────────────────────────────────────────────────────────


def _video_content(url: str, prompt: str) -> types.Content:
    """Build a Content with video FileData + text prompt."""
    return types.Content(
        parts=[
            types.Part(file_data=types.FileData(file_uri=url)),
            types.Part(text=prompt),
        ]
    )


async def _call_gemini_video(url: str, prompt: str, *, thinking_level: str = "high") -> str:
    return await GeminiClient.generate(
        _video_content(url, prompt),
        thinking_level=thinking_level,
    )


async def _get_title_summary(url: str, mode: str, thinking: str) -> dict[str, str]:
    prompt = PROMPTS[mode]["title_summary"]
    resp = await _call_gemini_video(url, prompt, thinking_level=thinking)
    title = _parse_labeled_line(resp, "TITLE")
    summary = _parse_labeled_line(resp, "SUMMARY")
    if not summary and "SUMMARY:" in resp.upper():
        parts = re.split(r"SUMMARY\s*:", resp, flags=re.IGNORECASE)
        if len(parts) > 1:
            summary = re.sub(r"\*+", "", parts[1]).strip()
    return {"title": title, "summary": summary}


async def _get_key_moments(url: str, mode: str, thinking: str) -> list[str]:
    prompt = PROMPTS[mode].get("key_moments", PROMPTS["general"]["key_moments"])
    resp = await _call_gemini_video(url, prompt, thinking_level=thinking)
    moments = [
        ln.strip()
        for ln in resp.split("\n")
        if ln.strip() and ("[" in ln or any(c.isdigit() for c in ln[:5]))
    ]
    return moments[:10]


async def _get_commands_tools(url: str, mode: str, thinking: str) -> dict[str, list[str]]:
    key = "commands_tools" if mode == "tutorial" else "commands_shortcuts"
    prompt = PROMPTS[mode].get(key, "")
    if not prompt:
        return {"commands": [], "tools": [], "shortcuts": [], "config": []}
    resp = await _call_gemini_video(url, prompt, thinking_level=thinking)
    commands = _parse_markdown_section(resp, "COMMANDS") or _parse_list_from_label(resp, "COMMANDS")
    shortcuts = _parse_markdown_section(resp, "SHORTCUTS") or _parse_list_from_label(
        resp, "SHORTCUTS"
    )
    config = _parse_markdown_section(resp, "CONFIG")
    mcp = _parse_markdown_section(resp, "MCP")
    tools = mcp if mcp else _parse_list_from_label(resp, "TOOLS")
    return {"commands": commands, "tools": tools, "shortcuts": shortcuts, "config": config}


async def _get_workflow_steps(url: str, mode: str, thinking: str) -> list[str]:
    key = "workflow_steps" if mode == "tutorial" else "workflow_features"
    prompt = PROMPTS[mode].get(key, "")
    if not prompt:
        return []
    resp = await _call_gemini_video(url, prompt, thinking_level=thinking)
    steps = [
        ln.strip()
        for ln in resp.split("\n")
        if ln.strip() and ("[" in ln or re.match(r"^\d+\.", ln.strip()) or ":" in ln[:20])
    ]
    return steps[:15]


async def _get_themes_sentiment(url: str, mode: str, thinking: str) -> dict:
    prompt = PROMPTS[mode].get("themes_sentiment", PROMPTS["general"]["themes_sentiment"])
    resp = await _call_gemini_video(url, prompt, thinking_level=thinking)
    return {
        "themes": _parse_list_from_label(resp, "THEMES"),
        "sentiment": _parse_labeled_line(resp, "SENTIMENT"),
    }


# ── Tools ─────────────────────────────────────────────────────────────────────


@video_server.tool()
async def video_analyze_youtube(
    url: str,
    mode: str = "general",
    thinking_level: str = "high",
    use_cache: bool = True,
) -> dict:
    """Analyse a YouTube video (general / tutorial / claude_code mode).

    Runs 3-4 parallel Gemini calls to extract title, summary, key moments,
    commands, workflow steps, themes, and sentiment. Zero-download — Gemini
    processes the video URL directly.
    """
    try:
        clean_url = _normalize_youtube_url(url)
        video_id = _extract_video_id(url)
    except ValueError as exc:
        return make_tool_error(exc)

    cfg = get_config()

    if use_cache:
        cached = cache_load(video_id, f"video_analyze_{mode}", cfg.default_model)
        if cached:
            cached["cached"] = True
            return cached

    try:
        tasks: list = [
            _get_title_summary(clean_url, mode, thinking_level),
            _get_key_moments(clean_url, mode, thinking_level),
        ]
        if mode == "general":
            tasks.append(_get_themes_sentiment(clean_url, mode, thinking_level))
        else:
            tasks.append(_get_commands_tools(clean_url, mode, thinking_level))
            tasks.append(_get_workflow_steps(clean_url, mode, thinking_level))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        if isinstance(results[0], Exception):
            return make_tool_error(results[0])

        analysis = VideoAnalysis(url=clean_url, mode=mode)
        ts = results[0]
        analysis.title = ts.get("title", "")
        analysis.summary = ts.get("summary", "")

        if not isinstance(results[1], Exception):
            analysis.key_moments = results[1]

        if mode == "general":
            if not isinstance(results[2], Exception):
                analysis.themes = results[2].get("themes", [])
                analysis.sentiment = results[2].get("sentiment", "")
        else:
            if not isinstance(results[2], Exception):
                cmd = results[2]
                analysis.commands = cmd.get("commands", [])
                analysis.tools_mentioned = cmd.get("tools", [])
                shortcuts = cmd.get("shortcuts", [])
                if shortcuts:
                    analysis.commands.extend(f"[shortcut] {s}" for s in shortcuts)
                config = cmd.get("config", [])
                if config:
                    analysis.code_snippets.extend(config)
            if len(results) > 3 and not isinstance(results[3], Exception):
                analysis.workflow_steps = results[3]

        out = analysis.model_dump()
        if use_cache:
            cache_save(video_id, f"video_analyze_{mode}", cfg.default_model, out)
        return out

    except Exception as exc:
        return make_tool_error(exc)


@video_server.tool()
async def video_compare(
    urls: list[str],
    mode: str = "general",
    thinking_level: str = "medium",
) -> dict:
    """Compare multiple YouTube videos — common themes, commands, unique aspects."""
    analyses = await asyncio.gather(
        *(video_analyze_youtube(u, mode=mode, thinking_level=thinking_level) for u in urls),
        return_exceptions=True,
    )
    valid = [a for a in analyses if isinstance(a, dict) and not a.get("error")]
    if not valid:
        return {"error": "No videos could be analysed", "category": "UNKNOWN", "hint": ""}

    text_parts = []
    for a in valid:
        text_parts.append(f"VIDEO: {a.get('title', a.get('url', ''))}")
        text_parts.append(f"  Summary: {a.get('summary', '')}")
        text_parts.append(f"  Themes: {', '.join(a.get('themes', []))}")
        text_parts.append(f"  Commands: {', '.join(a.get('commands', []))}")
        text_parts.append("")

    prompt = COMPARISON_TEMPLATE.format(analyses_text="\n".join(text_parts))
    resp = await GeminiClient.generate(prompt, thinking_level=thinking_level)
    return ComparisonResult(
        common_themes=_parse_list_from_label(resp, "COMMON_THEMES"),
        common_commands=_parse_list_from_label(resp, "COMMON_COMMANDS"),
        recommendation=_parse_labeled_line(resp, "RECOMMENDATION"),
    ).model_dump()


@video_server.tool()
async def video_extract_transcript(url: str) -> dict:
    """Extract a timestamped transcript from a YouTube video."""
    try:
        clean_url = _normalize_youtube_url(url)
    except ValueError as exc:
        return make_tool_error(exc)
    try:
        text = await _call_gemini_video(clean_url, TRANSCRIPT_EXTRACT)
        return {"url": clean_url, "transcript": text}
    except Exception as exc:
        return make_tool_error(exc)


@video_server.tool()
async def video_create_session(
    url: str,
    description: str = "",
    mode: str = "general",
) -> dict:
    """Create a persistent session for multi-turn video exploration."""
    try:
        clean_url = _normalize_youtube_url(url)
    except ValueError as exc:
        return make_tool_error(exc)

    # Get title via a quick call
    try:
        ts = await _get_title_summary(clean_url, mode, "low")
        title = ts.get("title", "")
    except Exception:
        title = ""

    session = session_store.create(clean_url, mode, video_title=title)
    return SessionInfo(
        session_id=session.session_id,
        status="created",
        video_title=title,
    ).model_dump()


@video_server.tool()
async def video_continue_session(session_id: str, prompt: str) -> dict:
    """Continue analysis within an existing video session."""
    session = session_store.get(session_id)
    if session is None:
        return {
            "error": f"Session {session_id} not found or expired",
            "category": "API_NOT_FOUND",
            "hint": "Create a new session with video_create_session",
        }

    user_content = types.Content(
        role="user",
        parts=[
            types.Part(file_data=types.FileData(file_uri=session.url)),
            types.Part(text=prompt),
        ],
    )
    contents = list(session.history) + [user_content]

    try:
        client = GeminiClient.get()
        cfg = get_config()
        response = await client.aio.models.generate_content(
            model=cfg.default_model,
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
            ),
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        text = "\n".join(p.text for p in parts if p.text and not getattr(p, "thought", False))

        model_content = types.Content(
            role="model",
            parts=[types.Part(text=text)],
        )
        turn = session_store.add_turn(session_id, user_content, model_content)
        return SessionResponse(response=text, turn_count=turn).model_dump()
    except Exception as exc:
        return make_tool_error(exc)
