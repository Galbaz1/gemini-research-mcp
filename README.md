# gemini-research-mcp

Gemini 3.1 Pro as a research partner for Claude Code — video analysis, deep research, content extraction, and web search. With progressive memory, automatic visualizations, and video frame extraction.

## The Problem

Claude Code can't natively analyze YouTube videos, run multi-phase research with evidence tiers, or extract structured data from PDFs/URLs. You need a second brain that can watch, read, and investigate.

## The Solution

11 instruction-driven tools powered by Gemini 3.1 Pro. Write a natural language instruction, get structured JSON back. No fixed modes — the LLM writes the instruction, Gemini executes it.

Every analysis automatically:
- **Saves progressively** to memory with timestamped sections and YAML frontmatter
- **Extracts video frames** at key moments (local files, via ffmpeg)
- **Generates an interactive visualization** (concept map, evidence network, or knowledge graph)
- **Captures a screenshot** via Playwright
- **Copies everything** to `output/<slug>/` in your workspace

## Use Cases

### Meeting recordings
Analyze a Teams/Zoom recording, get structured minutes with screenshots of shared screens:
```
/gr:video-chat ~/recordings/project-kickoff.mp4
> "This is a meeting between the dev team and the client. Create minutes in Dutch:
>  topics discussed, decisions made, action items per person.
>  Screenshot every shared screen."
```

### YouTube tutorials
Extract commands, workflows, and key concepts from technical videos:
```
/gr:video https://youtube.com/watch?v=...
```

### Research briefings
Deep-dive a topic with evidence-tier labeling (Confirmed → Speculation):
```
/gr:research "impact of EU AI Act on open-source model deployment"
```

### Academic papers
Analyze a PDF or arXiv paper, extract entities and relationships:
```
/gr:analyze https://arxiv.org/abs/2401.12345
/gr:analyze ~/papers/attention-is-all-you-need.pdf
```

### Knowledge review
Find gaps across all your past analyses:
```
/gr:recall fuzzy        # concepts you're unsure about
/gr:recall video        # list all video analyses
/gr:recall "kubernetes" # search across all notes
```

## Quickstart

```bash
# Install (one command)
npx gemini-research-mcp@latest

# Set your API key
export GEMINI_API_KEY="your-key-here"

# Use from any project
/gr:video https://youtube.com/watch?v=...
/gr:research "impact of EU AI Act on open-source models"
/gr:search "latest MCP protocol updates"
```

The installer copies commands, skills, and agents to `~/.claude/` and configures the MCP server to run via `uvx` from PyPI — no local clone needed.

```bash
# Other install options
npx gemini-research-mcp@latest --local     # Install to ./.claude/ (this project only)
npx gemini-research-mcp@latest --check     # Show install status
npx gemini-research-mcp@latest --uninstall # Clean removal
```

**Prerequisites**: Python >= 3.11, [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) >= 16, a [Google AI API key](https://aistudio.google.com/apikey)

**Optional**: [ffmpeg](https://ffmpeg.org/) (for video frame extraction)

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| **Tools** | 11 | Auto-start MCP server with video, research, content, search, infra tools |
| **Commands** | 6 | `/gr:video`, `/gr:video-chat`, `/gr:research`, `/gr:analyze`, `/gr:search`, `/gr:recall` |
| **Agents** | 2 | `researcher`, `video-analyst` — specialized subagents for complex tasks |
| **Skills** | 2 | Tool usage guide + visualization template system |

## Commands

All commands live under the `/gr:` namespace.

| Command | Description | Example |
|---------|-------------|---------|
| `/gr:video <source>` | One-shot video analysis with concept map + frame extraction | `/gr:video meeting.mp4` |
| `/gr:video-chat <source>` | Multi-turn video Q&A with progressive note-taking | `/gr:video-chat https://youtube.com/watch?v=...` |
| `/gr:research <topic>` | Deep research with evidence-tier network | `/gr:research "quantum computing breakthroughs"` |
| `/gr:analyze <content>` | Analyze any URL, file, or text with knowledge graph | `/gr:analyze https://arxiv.org/abs/2401.12345` |
| `/gr:search <query>` | Web search via Gemini grounding | `/gr:search "latest MCP protocol updates"` |
| `/gr:recall [filter]` | Browse past analyses, filter by category or knowledge state | `/gr:recall fuzzy` |

### What Happens When You Run a Command

```
/gr:video-chat ~/recordings/call.mp4
> "Summarize this meeting, extract action items, screenshot shared screens"

 Phase 1  Gemini analyzes the video (any language)
 Phase 2  Initial results saved to memory immediately
 Phase 2.5  ffmpeg extracts frames at key visual moments (local files only)
 Phase 3  Agent enriches with concepts + relationships
 Phase 4  Interactive concept map HTML generated
 Phase 5  Playwright screenshots the visualization
 Phase 6  Everything linked in analysis.md
 Phase 7  All artifacts copied to output/<slug>/ in your workspace
```

### Output Structure

Every analysis produces a directory with all artifacts:

```
output/call-meeting-2026-02-27/
├── analysis.md              # Timestamped analysis with YAML frontmatter
├── frames/                  # Screenshots extracted from the video
│   ├── frame_0450.png       # "Architecture diagram shown at 4:50"
│   ├── frame_1230.png       # "Dashboard demo at 12:30"
│   └── ...
├── concept-map.html         # Interactive visualization (open in browser)
└── screenshot.png           # Static capture of the concept map
```

The same artifacts are also saved to Claude's memory (`~/.claude/projects/<project>/memory/gr/`) for cross-session recall via `/gr:recall`.

### Knowledge States

Each `analysis.md` includes YAML frontmatter tracking what you know:

```yaml
concepts:
  - name: "Latent Demand"
    state: fuzzy         # know | fuzzy | unknown
    timestamp: "12:15"
  - name: "Jevons Paradox"
    state: unknown
    timestamp: "30:26"
```

Use `/gr:recall fuzzy` to find concepts you're unsure about across all analyses. The interactive visualizations let you cycle knowledge states (click a node) and generate a targeted study prompt.

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
| `video_analyze` | Instruction-driven video analysis — YouTube URLs or local files, with optional custom output schema |
| `video_create_session` | Start multi-turn video exploration session |
| `video_continue_session` | Follow-up questions within a session |

### Research (3)

| Tool | Description |
|------|-------------|
| `research_deep` | Multi-phase deep analysis with evidence tiers (CONFIRMED → SPECULATION) |
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

### npx Installer (recommended)

```bash
npx gemini-research-mcp@latest
```

Installs commands, skills, agents, and MCP config. The server runs via `uvx gemini-research-mcp` from PyPI — no local clone needed.

### Standalone MCP Server

If you only need the 11 tools (no commands/skills/agents), add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "gemini-research": {
      "command": "uvx",
      "args": ["gemini-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

### Claude Desktop

Tools only (no commands, skills, agents, or Playwright integration). Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gemini-research": {
      "command": "uvx",
      "args": ["gemini-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

### From Source (development)

```bash
git clone https://github.com/Galbaz1/gemini-research-mcp
cd gemini-research-mcp
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"
node bin/install.js --global
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
| No frames extracted | Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| Visualization not generated | Playwright runs via npx — ensure Node.js is available on PATH |
| Screenshot capture fails | The HTML visualization is still saved; screenshot is a bonus artifact |

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

For security vulnerabilities, please see [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Author

**Fausto Albers**

Lead Gen AI Research & Development at the [Industrial Digital Twins Lab](https://www.hva.nl), Amsterdam University of Applied Sciences (HvA), in the research group of Jurjen Helmus.

Founder of [Wonder Why](https://wonderwhy.ai).

## License

MIT
