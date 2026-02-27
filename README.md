# gemini-research-mcp

Gemini 3.1 Pro as a research partner for Claude Code — video analysis, deep research, content extraction, and web search. With progressive memory and automatic visualizations.

## The Problem

Claude Code can't natively analyze YouTube videos, run multi-phase research with evidence tiers, or extract structured data from PDFs/URLs. You need a second brain that can watch, read, and investigate.

## The Solution

11 instruction-driven tools powered by Gemini 3.1 Pro. Write a natural language instruction, get structured JSON back. No fixed modes — the LLM writes the instruction, Gemini executes it.

Every analysis automatically saves progressively to memory, generates an interactive visualization (concept map, evidence network, or knowledge graph), and captures a screenshot — no manual steps.

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
| **Commands** | 6 | `/gr:video`, `/gr:research`, `/gr:analyze`, `/gr:video-chat`, `/gr:search`, `/gr:recall` |
| **Agents** | 2 | `researcher`, `video-analyst` — specialized subagents for complex tasks |
| **Skills** | 2 | Tool usage guide + visualization template system |

## Commands

All commands live under the `/gr:` namespace.

| Command | Description | Example |
|---------|-------------|---------|
| `/gr:video <url>` | Video analysis with concept map | `/gr:video https://youtube.com/watch?v=...` |
| `/gr:video-chat <url>` | Multi-turn video Q&A session | `/gr:video-chat https://youtube.com/watch?v=...` |
| `/gr:research <topic>` | Deep research with evidence network | `/gr:research quantum computing breakthroughs 2026` |
| `/gr:analyze <content>` | Analyze any URL, file, or text with knowledge graph | `/gr:analyze https://arxiv.org/abs/...` |
| `/gr:search <query>` | Web search via Gemini grounding | `/gr:search latest MCP protocol updates` |
| `/gr:recall [topic]` | Browse past analyses with knowledge state filtering | `/gr:recall fuzzy` |

### Memory & Visualization

Every `/gr:video`, `/gr:research`, and `/gr:analyze` command automatically:

1. **Saves progressively** — results are written immediately, then enriched in place with relationships and metadata
2. **Generates an interactive visualization** — concept map, evidence network, or knowledge graph (single-file HTML)
3. **Takes a Playwright screenshot** — static PNG capture of the visualization
4. **Stores everything together** in `gr/<category>/<slug>/`:

```
gr/video/boris-cherny/
├── analysis.md          # Timestamped analysis with YAML frontmatter
├── concept-map.html     # Interactive visualization (drag, zoom, filter)
└── screenshot.png       # Static capture
```

Each `analysis.md` includes YAML frontmatter with knowledge states per concept (`know`, `fuzzy`, `unknown`). Use `/gr:recall fuzzy` to find concepts you're fuzzy on across all analyses.

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

The plugin auto-starts the MCP server, registers commands, agents, and skills. Playwright is bundled for screenshot capture (runs headless, no visible browser).

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

Note: Standalone mode provides the 11 tools but not the commands, agents, skills, or Playwright integration. Use the plugin install for the full experience.

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
| Visualization not generated | Playwright runs via npx — ensure Node.js is available on PATH |
| Screenshot capture fails | The HTML visualization is still saved; screenshot is a bonus artifact |

## License

MIT
