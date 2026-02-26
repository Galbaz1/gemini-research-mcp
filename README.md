# gemini-research-mcp

Unified Gemini research partner — video analysis, deep research, and content extraction via MCP.

Powered by **Gemini 3.1 Pro** with thinking-level support. Zero-download YouTube analysis, evidence-tier labeling, multi-turn sessions, and file-based caching.

## Install

```bash
# From PyPI (when published)
uvx gemini-research-mcp

# From source
git clone <repo-url>
cd gemini-research-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Configure for Claude Code

Add to your `.mcp.json`:

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

Or for local development:

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

## Tools (15)

### Video Analysis (5)

| Tool | Description |
|------|-------------|
| `video_analyze_youtube` | Analyse a YouTube video in general/tutorial/claude_code mode |
| `video_compare` | Compare multiple videos — common themes, unique aspects |
| `video_extract_transcript` | Extract timestamped transcript |
| `video_create_session` | Create persistent multi-turn session |
| `video_continue_session` | Continue analysis within a session |

### Research (3)

| Tool | Description |
|------|-------------|
| `research_deep` | Multi-phase deep analysis with evidence tiers |
| `research_plan` | Generate multi-agent orchestration blueprint |
| `research_assess_evidence` | Assess a claim against sources |

### Content Analysis (3)

| Tool | Description |
|------|-------------|
| `content_analyze_document` | Analyse PDF, text, or URL |
| `content_summarize` | Summarize at brief/medium/detailed level |
| `content_structured_extract` | Extract structured data via JSON Schema |

### Web (2)

| Tool | Description |
|------|-------------|
| `web_search` | Google Search via Gemini grounding |
| `web_analyze_url` | Fetch and analyse any URL |

### Infrastructure (2)

| Tool | Description |
|------|-------------|
| `infra_cache` | Cache management (stats/list/clear) |
| `infra_configure` | Runtime reconfiguration |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google AI API key |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Default model |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | Flash model for search |
| `GEMINI_THINKING_LEVEL` | `high` | Default thinking level |
| `GEMINI_TEMPERATURE` | `1.0` | Default temperature |
| `GEMINI_CACHE_DIR` | `~/.cache/gemini-research-mcp/` | Cache location |
| `GEMINI_CACHE_TTL_DAYS` | `30` | Cache expiry |

## Development

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

## License

MIT
