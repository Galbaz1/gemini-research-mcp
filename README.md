# video-research-mcp

Give Claude Code a Gemini-powered research partner that can watch videos, read papers, search the web, and remember everything.

## Why

Claude Code has no native way to analyze video, run multi-source research with evidence grading, or keep findings across sessions. This plugin adds those capabilities through 22 MCP tools powered by Gemini 3.1 Pro, with optional persistent storage via Weaviate.

## Install

```bash
npx video-research-mcp@latest
export GEMINI_API_KEY="your-key-here"
```

That's it. The installer copies 8 commands, 3 skills, and 4 agents to `~/.claude/` and configures the MCP server to run via `uvx` from PyPI.

```bash
npx video-research-mcp@latest --check     # show install status
npx video-research-mcp@latest --uninstall  # clean removal
npx video-research-mcp@latest --local      # install for this project only
```

**Requires**: Python >= 3.11, [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) >= 16, a [Google AI API key](https://aistudio.google.com/apikey)

## What you can do

### Analyze a meeting recording

```
/gr:video-chat ~/recordings/project-kickoff.mp4
> "Create minutes in Dutch: topics discussed, decisions made, action items per person.
>  Screenshot every shared screen."
```

Gemini watches the entire video, extracts content in any language. For local files, ffmpeg pulls frames at key visual moments. The output goes to `output/<slug>/` in your workspace with analysis, frames, and an interactive concept map.

### Research a topic

```
/gr:research "impact of EU AI Act on open-source model deployment"
```

Runs `web_search` and `research_deep` in parallel. Findings are graded into evidence tiers (Confirmed, Supported, Inference, Speculation) and visualized as an interactive evidence network.

### Analyze a paper or URL

```
/gr:analyze https://arxiv.org/abs/2401.12345
/gr:analyze ~/papers/attention-is-all-you-need.pdf
```

Works with PDFs, URLs, and raw text. Extracts entities, relationships, and key arguments. Produces a knowledge graph visualization.

### Search the web

```
/gr:search "latest developments in MCP protocol"
```

Google Search via Gemini grounding with source citations.

### Recall past work

```
/gr:recall fuzzy         # concepts you're unsure about
/gr:recall "kubernetes"  # search across all notes
```

Searches your analysis memory. Each analysis tracks knowledge states (know / fuzzy / unknown) in YAML frontmatter, so you can find gaps.

### Build up knowledge while you code

The plugin works as a research companion during development. You encounter an unfamiliar concept, research it, and the findings are stored automatically. Next week, when you run into the same topic, `knowledge_search` or `knowledge_ask` retrieves what you learned -- across projects, across sessions.

```
# While working on a project, you hit something you don't understand
/gr:research "HNSW index parameters for high-dimensional embeddings"

# Two weeks later, in a different project
knowledge_search(query="HNSW tuning")           # finds your earlier research
knowledge_ask(query="What did I learn about ef_construction?")  # AI-generated summary
```

### Use it as an MCP server in your own application

The 22 tools are standard MCP -- any MCP client can call them. Point your app at the server and you get Gemini-powered video analysis, research, and knowledge retrieval as API calls. No Claude Code required.

```json
{
  "mcpServers": {
    "video-research": {
      "command": "uvx",
      "args": ["video-research-mcp"],
      "env": { "GEMINI_API_KEY": "${GEMINI_API_KEY}" }
    }
  }
}
```

## Commands

| Command | What it does |
|---------|-------------|
| `/gr:video <source>` | One-shot video analysis with concept map and frame extraction |
| `/gr:video-chat <source>` | Multi-turn video Q&A with progressive note-taking |
| `/gr:research <topic>` | Deep research with evidence-tier labeling |
| `/gr:analyze <content>` | Analyze any URL, file, or text |
| `/gr:search <query>` | Web search via Gemini grounding |
| `/gr:recall [filter]` | Browse past analyses from memory |
| `/gr:models [preset]` | Switch Gemini model preset (best/stable/budget) |
| `/gr:doctor [quick|full]` | Diagnose MCP wiring, API keys, and Weaviate connectivity (`quick` is compact, `full` is verbose) |

### How a command runs

```
/gr:video-chat ~/recordings/call.mp4
> "Summarize this meeting, extract action items"

 Phase 1   Gemini analyzes the video
 Phase 2   Results saved to memory
 Phase 2.5 ffmpeg extracts frames (local files only)
 Phase 3   Concepts and relationships enriched
 Phase 4   Interactive visualization generated (opt-in)
 Phase 5   Playwright screenshots it
 Phase 6   Everything copied to output/<slug>/
```

Background agents handle visualization and YouTube comment analysis without blocking the conversation.

### Output

```
output/project-kickoff-2026-02-28/
├── analysis.md          # timestamped analysis with YAML frontmatter
├── frames/              # extracted video frames (local files)
├── concept-map.html     # interactive visualization
└── screenshot.png       # static capture
```

The same files are also saved to Claude's project memory for `/gr:recall`.

## Knowledge store

When `WEAVIATE_URL` is set, every tool automatically stores its results in Weaviate. Without it, nothing changes -- the plugin works the same, you just don't get persistent search.

Seven collections are created on first connection:

| Collection | Filled by |
|------------|-----------|
| `ResearchFindings` | `research_deep`, `research_assess_evidence` |
| `VideoAnalyses` | `video_analyze`, `video_batch_analyze` |
| `ContentAnalyses` | `content_analyze` |
| `VideoMetadata` | `video_metadata` |
| `SessionTranscripts` | `video_continue_session` |
| `WebSearchResults` | `web_search` |
| `ResearchPlans` | `research_plan` |

Seven knowledge tools let you query this data: hybrid search, semantic similarity, fetch by UUID, manual ingest, collection stats. Two additional tools (`knowledge_ask` and `knowledge_query`) use Weaviate's QueryAgent for AI-generated answers with source citations -- these require the optional `weaviate-agents` package:

```bash
uv pip install 'video-research-mcp[agents]'
```

To set up Weaviate, run the interactive onboarding:

```
/skill weaviate-setup
```

Or set the environment variables directly:

```bash
export WEAVIATE_URL="https://your-cluster.weaviate.network"
export WEAVIATE_API_KEY="your-key"
```

<details>
<summary><strong>All 22 tools</strong></summary>

### Video (4)

| Tool | Description |
|------|-------------|
| `video_analyze` | Analyze YouTube URLs or local video files with a natural language instruction |
| `video_create_session` | Start a multi-turn video Q&A session |
| `video_continue_session` | Ask follow-up questions within a session |
| `video_batch_analyze` | Analyze all video files in a directory concurrently |

### YouTube (3)

| Tool | Description |
|------|-------------|
| `video_metadata` | Fetch video metadata (title, views, duration, tags) via YouTube Data API |
| `video_comments` | Fetch top-level comments with like counts and reply counts |
| `video_playlist` | List videos in a YouTube playlist |

### Research (3)

| Tool | Description |
|------|-------------|
| `research_deep` | Multi-phase research with evidence tiers (Confirmed through Speculation) |
| `research_plan` | Generate a research orchestration blueprint |
| `research_assess_evidence` | Assess a specific claim against sources with confidence scoring |

### Content (2)

| Tool | Description |
|------|-------------|
| `content_analyze` | Analyze a file, URL, or raw text with a natural language instruction |
| `content_extract` | Extract structured data using a caller-provided JSON schema |

### Search (1)

| Tool | Description |
|------|-------------|
| `web_search` | Google Search via Gemini grounding with source citations |

### Infrastructure (2)

| Tool | Description |
|------|-------------|
| `infra_cache` | View, list, or clear the analysis cache |
| `infra_configure` | Change model, thinking level, or temperature at runtime |

### Knowledge (7)

| Tool | Description |
|------|-------------|
| `knowledge_search` | Hybrid, semantic, or keyword search across collections |
| `knowledge_related` | Find semantically similar objects by UUID |
| `knowledge_stats` | Object counts per collection, with optional group-by |
| `knowledge_fetch` | Retrieve a single object by UUID |
| `knowledge_ingest` | Insert data into a collection (validated against schema) |
| `knowledge_ask` | AI-generated answer with source citations (needs `weaviate-agents`) |
| `knowledge_query` | Natural language object retrieval (needs `weaviate-agents`) |

</details>

## Other install methods

### Standalone MCP server

If you only need the tools (no commands, skills, or agents):

```json
{
  "mcpServers": {
    "video-research": {
      "command": "uvx",
      "args": ["video-research-mcp"],
      "env": { "GEMINI_API_KEY": "${GEMINI_API_KEY}" }
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "video-research": {
      "command": "uvx",
      "args": ["video-research-mcp"],
      "env": { "GEMINI_API_KEY": "your-key-here" }
    }
  }
}
```

### From source

```bash
git clone https://github.com/Galbaz1/video-research-mcp
cd video-research-mcp
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"
node bin/install.js --global
```

## Configuration

| Variable | Default | What it does |
|----------|---------|-------------|
| `GEMINI_API_KEY` | **(required)** | Google AI API key |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Primary model |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | Fast model for search |
| `GEMINI_THINKING_LEVEL` | `high` | Thinking depth (minimal / low / medium / high) |
| `GEMINI_TEMPERATURE` | `1.0` | Sampling temperature |
| `GEMINI_CACHE_DIR` | `~/.cache/video-research-mcp/` | Cache directory |
| `GEMINI_CACHE_TTL_DAYS` | `30` | Cache expiry |
| `GEMINI_MAX_SESSIONS` | `50` | Max concurrent video sessions |
| `GEMINI_SESSION_TIMEOUT_HOURS` | `2` | Session TTL |
| `GEMINI_SESSION_MAX_TURNS` | `24` | Max turns per session |
| `GEMINI_SESSION_DB` | `""` | SQLite path for session persistence (empty = in-memory) |
| `YOUTUBE_API_KEY` | `""` | YouTube Data API key (falls back to `GEMINI_API_KEY`) |
| `WEAVIATE_URL` | `""` | Weaviate URL (empty = knowledge store disabled) |
| `WEAVIATE_API_KEY` | `""` | Required for Weaviate Cloud |

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run pytest tests/ -v        # 417 tests, all mocked
uv run ruff check src/ tests/  # lint
```

## Agent Teams

This project uses Claude Code agent teams powered by **Claude Opus 4.6** for parallel development workflows. Every subagent team defaults to Opus 4.6 unless the user explicitly specifies otherwise.

| Workflow | Agents | What they do |
|----------|--------|-------------|
| Dependency audit | 3 parallel | Constraint analysis, compatibility scanning, API surface verification |
| Code review | 3 parallel | Security, architecture, test coverage |
| Feature development | 2-4 parallel | Implementation with file ownership boundaries |

Agent teams are spawned via Claude Code's `Agent` tool with `model: "opus"`. The team lead coordinates task decomposition, file ownership, and result synthesis. Teammates communicate through the built-in messaging system and share a task list for coordination.

To change the default model for a specific task:
```python
# In Agent tool call
"model": "sonnet"  # override for lightweight tasks
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No API key error | Set `GEMINI_API_KEY` |
| 429 / quota exceeded | Wait 60s, or try `/gr:models budget` for higher limits |
| Video analysis empty | Video may be private, age-restricted, or region-locked |
| No frames extracted | Install ffmpeg: `brew install ffmpeg` |
| Visualization missing | Ensure Node.js is on PATH (Playwright runs via npx) |
| Weaviate won't connect | Check `WEAVIATE_URL` and that the instance is running |
| Knowledge tools empty | Set `WEAVIATE_URL` to enable |
| `weaviate-agents not installed` | `uv pip install 'video-research-mcp[agents]'` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR guidelines. See [ROADMAP.md](ROADMAP.md) for planned features and contribution opportunities. Report security issues via [SECURITY.md](SECURITY.md).

## Author

**Fausto Albers** -- Lead Gen AI Research & Development at the [Industrial Digital Twins Lab](https://www.hva.nl), Amsterdam University of Applied Sciences (HvA), in the research group of Jurjen Helmus. Founder of [Wonder Why](https://wonderwhy.ai).

## License

MIT
