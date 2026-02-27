# gemini-research-mcp

Gemini 3.1 Pro as a research partner for Claude Code — video analysis, deep research, content extraction, and web search.

## The Problem

Claude Code can't natively analyze YouTube videos, run multi-phase research with evidence tiers, or extract structured data from PDFs/URLs. You need a second brain that can watch, read, and investigate.

## The Solution

11 instruction-driven tools powered by Gemini 3.1 Pro. Write a natural language instruction, get structured JSON back. No fixed modes — the LLM writes the instruction, Gemini executes it.

## Quickstart

```bash
# 1. Clone
git clone https://github.com/YOUR_ORG/gemini-research-mcp
cd gemini-research-mcp

# 2. Set your API key
export GEMINI_API_KEY="your-key-here"

# 3. Install as plugin
claude plugin add /path/to/gemini-research-mcp
```

**Prerequisites**: Python >= 3.11, [uv](https://docs.astral.sh/uv/), a [Google AI API key](https://aistudio.google.com/apikey)

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| **Tools** | 11 | Auto-start MCP server with video, research, content, search, infra tools |
| **Commands** | 3 | `/research`, `/video`, `/analyze` — quick-access workflows |
| **Agents** | 2 | `researcher`, `video-analyst` — specialized subagents for complex tasks |
| **Skill** | 1 | Tool usage guide auto-loaded into Claude's context |

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/research <topic>` | Multi-phase deep research with evidence tiers | `/research quantum computing breakthroughs 2026` |
| `/video <url>` | Comprehensive YouTube video analysis | `/video https://youtube.com/watch?v=...` |
| `/analyze <content>` | Analyze any URL, file, or text | `/analyze https://arxiv.org/abs/...` |

## Tool Selection Guide

| I want to... | Use this tool |
|---|---|
| Analyze a YouTube video | `video_analyze` |
| Multi-turn video Q&A | `video_create_session` + `video_continue_session` |
| Research a topic in depth | `research_deep` |
| Plan a research strategy | `research_plan` |
| Verify a specific claim | `research_assess_evidence` |
| Analyze a URL, file, or text | `content_analyze` |
| Extract structured data | `content_extract` |
| Search the web | `web_search` |
| Manage analysis cache | `infra_cache` |
| Change model/thinking/temp | `infra_configure` |

## Tools (11)

### Video (3)

| Tool | Description |
|------|-------------|
| `video_analyze` | Instruction-driven YouTube analysis with optional custom output schema |
| `video_create_session` | Start multi-turn video exploration session |
| `video_continue_session` | Follow-up questions within a session |

### Research (3)

| Tool | Description |
|------|-------------|
| `research_deep` | Multi-phase deep analysis with evidence tiers (CONFIRMED > SPECULATION) |
| `research_plan` | Generate research orchestration blueprint |
| `research_assess_evidence` | Assess a claim against sources with confidence scoring |

### Content (2)

| Tool | Description |
|------|-------------|
| `content_analyze` | Analyze file (PDF/text), URL, or raw text with instruction |
| `content_extract` | Extract structured data via caller-provided JSON Schema |

### Search (1)

| Tool | Description |
|------|-------------|
| `web_search` | Google Search via Gemini grounding with source citations |

### Infrastructure (2)

| Tool | Description |
|------|-------------|
| `infra_cache` | Cache management — stats, list entries, clear by content ID |
| `infra_configure` | Runtime overrides for model, thinking level, temperature |

## Installation

### As Claude Code Plugin (recommended)

```bash
claude plugin add /path/to/gemini-research-mcp
```

The plugin auto-starts the MCP server, registers commands, agents, and the skill.

### Standalone MCP Server

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "gemini-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/gemini-research-mcp", "gemini-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gemini-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/gemini-research-mcp", "gemini-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

### VS Code (Copilot MCP)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "gemini-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/gemini-research-mcp", "gemini-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | **(required)** | Google AI API key |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Default model |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | Flash model for search |
| `GEMINI_THINKING_LEVEL` | `high` | Default thinking level (minimal/low/medium/high) |
| `GEMINI_TEMPERATURE` | `1.0` | Default temperature |
| `GEMINI_CACHE_DIR` | `~/.cache/gemini-research-mcp/` | Cache location |
| `GEMINI_CACHE_TTL_DAYS` | `30` | Cache expiry in days |
| `GEMINI_MAX_SESSIONS` | `50` | Max concurrent video sessions |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `2` | Session TTL |
| `GEMINI_SESSION_MAX_TURNS` | `24` | Max retained turns per session |

## Development

```bash
# Install dev dependencies
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests (all mocked, no API calls needed)
uv run pytest tests/ -v

# Lint (line-length=100, target py311)
uv run ruff check src/ tests/
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No Gemini API key` error | Set `GEMINI_API_KEY` env var |
| `429` / quota exceeded | Wait 60s or upgrade your Google AI plan |
| Cache permission errors | Check write access to `~/.cache/gemini-research-mcp/` or set `GEMINI_CACHE_DIR` |
| Video analysis returns empty | Video may be private, age-restricted, or region-locked |
| Plugin not loading | Verify `python >= 3.11` and `uv` are available on PATH |

## License

MIT
