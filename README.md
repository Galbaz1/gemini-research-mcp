# video-research-mcp

Give Claude Code a Gemini-powered research partner that can watch videos, read papers, search the web, and remember everything.

## Why

Claude Code can't analyze video, run multi-source research with evidence grading, or keep findings across sessions. This plugin adds those capabilities through three MCP servers powered by Gemini 3.1 Pro, with optional persistent storage via Weaviate.

| Server | Tools | What it does |
|--------|-------|-------------|
| **video-research-mcp** | 24 | Video analysis, deep research, content extraction, web search, knowledge store |
| **video-explainer-mcp** | 15 | Synthesize explainer videos from research content (wraps [video_explainer](https://github.com/prajwal-y/video_explainer) CLI) |
| **video-agent-mcp** | 2 | Parallel scene generation for the explainer pipeline (Claude Agent SDK) |

540 tests, all mocked. No test hits the real API.

## Install

```bash
npx video-research-mcp@latest
export GEMINI_API_KEY="your-key-here"
```

The installer copies 13 commands, 5 skills, and 6 agents to `~/.claude/` and configures the MCP servers to run via `uvx` from PyPI.

```bash
npx video-research-mcp@latest --check     # show install status
npx video-research-mcp@latest --uninstall  # clean removal
npx video-research-mcp@latest --local      # install for this project only
```

**Requires**: Python >= 3.11, [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) >= 16, a [Google AI API key](https://aistudio.google.com/apikey)

## Quick start

### Analyze a meeting recording

```
/gr:video-chat ~/recordings/project-kickoff.mp4
> "Create minutes in Dutch: topics discussed, decisions made, action items per person.
>  Screenshot every shared screen."
```

Gemini watches the entire video and extracts content in any language. For local files, ffmpeg pulls frames at key visual moments. Large local files (>=20MB) are uploaded to Gemini's File API and context-cached automatically -- multi-turn follow-ups reuse the cache instead of re-ingesting the full video. Output goes to `output/<slug>/` with analysis, frames, and an interactive concept map.

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

### Compare a folder of documents

```
/gr:analyze ~/papers/
```

Scans the directory, passes all PDFs and text files to Gemini in one call, and returns a cross-document comparative analysis. Supports PDF, TXT, MD, HTML, XML, JSON, CSV.

### Deep research in source documents

```
/gr:research-doc ~/papers/
/gr:research-doc paper1.pdf paper2.pdf "Compare methodologies and find contradictions"
```

Runs a 4-phase pipeline -- Document Mapping, Evidence Extraction, Cross-Reference, Synthesis -- with every claim cited back to document and page number. Evidence tiers apply to document content, not web inference. Documents are uploaded to Gemini's File API once and reused across all phases.

### Search the web

```
/gr:search "latest developments in MCP protocol"
```

Google Search via Gemini grounding with source citations.

### Recall past work

```
/gr:recall                          # overview: knowledge store stats + saved analyses
/gr:recall "kubernetes"             # semantic search (Weaviate) + filesystem grep
/gr:recall fuzzy                    # concepts you're unsure about
/gr:recall ask "what do I know about X?"  # AI-powered Q&A with source citations
/gr:recall research                 # filter by category
```

When Weaviate is configured, keyword searches use semantic matching -- find "gradient descent tuning" even when you searched for "ML optimization". Without Weaviate, recall falls back to exact keyword grep.

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

The tools are standard MCP -- any MCP client can call them. Point your app at the server and you get Gemini-powered video analysis, research, and knowledge retrieval as API calls. No Claude Code required.

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
| `/gr:research-doc <files>` | Evidence-tiered research grounded in source documents |
| `/gr:analyze <content>` | Analyze any URL, file, text, or directory of documents |
| `/gr:search <query>` | Web search via Gemini grounding |
| `/gr:recall [filter]` | Browse past analyses from memory |
| `/gr:models [preset]` | Switch Gemini model preset (best/stable/budget) |
| `/gr:explainer <project>` | Create and manage explainer video projects |
| `/gr:explain-video <project>` | Generate a full explainer video from project content |
| `/gr:explain-status <project>` | Check render progress and pipeline state |
| `/gr:traces [filter]` | Query, debug, and evaluate MLflow traces from Gemini tool calls |
| `/gr:doctor [quick\|full]` | Diagnose MCP wiring, API keys, Weaviate, and MLflow connectivity |

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

### Debug Gemini traces

```
/gr:traces                       # recent traces overview
/gr:traces errors                # filter for failed traces
/gr:traces slow                  # filter for traces over 5 seconds
/gr:traces tr-abc123             # get trace detail
/gr:traces feedback tr-abc123 4  # log human feedback (score 1-5)
```

When MLflow tracing is enabled (`MLFLOW_TRACKING_URI` is set), every Gemini API call is captured automatically. The `/gr:traces` command queries these via the MLflow MCP server -- no Python code needed.

## Tool overview

<details>
<summary><strong>video-research-mcp (24 tools)</strong></summary>

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

### Research (4)

| Tool | Description |
|------|-------------|
| `research_deep` | Multi-phase research with evidence tiers (Confirmed through Speculation) |
| `research_plan` | Generate a research orchestration blueprint |
| `research_assess_evidence` | Assess a specific claim against sources with confidence scoring |
| `research_document` | 4-phase evidence-tiered pipeline grounded in source documents |

### Content (3)

| Tool | Description |
|------|-------------|
| `content_analyze` | Analyze a file, URL, or raw text with a natural language instruction |
| `content_batch_analyze` | Compare or batch-analyze a directory or file list (compare/individual modes) |
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
| `knowledge_search` | Hybrid, semantic, or keyword search across collections (with optional Cohere reranking) |
| `knowledge_related` | Find semantically similar objects by UUID |
| `knowledge_stats` | Object counts per collection, with optional group-by |
| `knowledge_fetch` | Retrieve a single object by UUID |
| `knowledge_ingest` | Insert data into a collection (validated against schema) |
| `knowledge_ask` | AI-generated answer with source citations (needs `weaviate-agents`) |
| `knowledge_query` | **[Deprecated]** Natural language object retrieval -- use `knowledge_search` instead |

</details>

<details>
<summary><strong>video-explainer-mcp (15 tools)</strong></summary>

### Project (4)

| Tool | Description |
|------|-------------|
| `explainer_create` | Create a new explainer video project |
| `explainer_inject` | Inject research content into a project |
| `explainer_status` | Check project state and step completion |
| `explainer_list` | List all explainer projects |

### Pipeline (6)

| Tool | Description |
|------|-------------|
| `explainer_generate` | Generate all steps in the explainer pipeline |
| `explainer_step` | Run a single pipeline step |
| `explainer_render` | Render the final video (blocking) |
| `explainer_render_start` | Start a background render, returns job ID |
| `explainer_render_poll` | Check progress of a background render |
| `explainer_short` | Generate a short-form video clip |

### Quality (3)

| Tool | Description |
|------|-------------|
| `explainer_refine` | Refine generated content with feedback |
| `explainer_feedback` | Submit quality feedback on a step |
| `explainer_factcheck` | Fact-check generated narration against sources |

### Audio (2)

| Tool | Description |
|------|-------------|
| `explainer_sound` | Add sound effects to scenes |
| `explainer_music` | Add background music |

</details>

<details>
<summary><strong>video-agent-mcp (2 tools)</strong></summary>

| Tool | Description |
|------|-------------|
| `agent_generate_scenes` | Generate all scenes in parallel using Claude Agent SDK |
| `agent_generate_single_scene` | Generate a single scene (used as a subtask by the parallel tool) |

</details>

## Knowledge store

When `WEAVIATE_URL` is set, every tool automatically stores its results in Weaviate. Without it, nothing changes -- the plugin works the same, you just don't get persistent search.

Eleven collections are created on first connection:

| Collection | Filled by |
|------------|-----------|
| `ResearchFindings` | `research_deep`, `research_assess_evidence`, `research_document` |
| `VideoAnalyses` | `video_analyze`, `video_batch_analyze` |
| `ContentAnalyses` | `content_analyze`, `content_batch_analyze` |
| `VideoMetadata` | `video_metadata` |
| `SessionTranscripts` | `video_continue_session` |
| `WebSearchResults` | `web_search` |
| `ResearchPlans` | `research_plan` |
| `CommunityReactions` | comment analysis (via `/gr:video` agent) |
| `ConceptKnowledge` | concept extraction from analyses |
| `RelationshipEdges` | relationship mapping between concepts |
| `CallNotes` | meeting/call analysis notes |

Knowledge tools are also accessible through `/gr:recall`, which combines semantic search with filesystem browsing in one interface.

Seven knowledge tools let you query this data: hybrid search (with optional Cohere reranking), semantic similarity, fetch by UUID, manual ingest, collection stats. `knowledge_ask` uses Weaviate's QueryAgent for AI-generated answers with source citations (requires the optional `weaviate-agents` package). `knowledge_query` is deprecated -- use `knowledge_search` instead.

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

## Configuration

| Variable | Default | What it does |
|----------|---------|-------------|
| `GEMINI_API_KEY` | **(required)** | Google AI API key |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Primary model |
| `GEMINI_FLASH_MODEL` | `gemini-3-flash-preview` | Fast model for search and summaries |
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
| `MLFLOW_TRACKING_URI` | `""` | MLflow server URL (empty = tracing disabled) |
| `MLFLOW_EXPERIMENT_NAME` | `video-research-mcp` | MLflow experiment name |
| `EXPLAINER_PATH` | `""` | Path to cloned video_explainer repo |
| `EXPLAINER_TTS_PROVIDER` | `"mock"` | TTS provider: mock, elevenlabs, openai, gemini, edge |

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

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run pytest tests/ -v        # 540 tests, all mocked
uv run ruff check src/ tests/  # lint
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
| MLflow tools unavailable | Set `MLFLOW_TRACKING_URI` and start `mlflow server --port 5001` |
| No traces captured | Ensure `MLFLOW_TRACKING_URI` is set in the server environment |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR guidelines. See [ROADMAP.md](ROADMAP.md) for planned features and contribution opportunities. Report security issues via [SECURITY.md](SECURITY.md).

## Author

**Fausto Albers** -- Lead Gen AI Research & Development at the [Industrial Digital Twins Lab](https://www.hva.nl), Amsterdam University of Applied Sciences (HvA), in the research group of Jurjen Helmus. Founder of [Wonder Why](https://wonderwhy.ai).

## Credits

This project builds on outstanding open-source work:

- **[video_explainer](https://github.com/prajwal-y/video_explainer)** by [prajwal-y](https://github.com/prajwal-y) -- the video synthesis engine at the heart of our explainer pipeline. We extended it with configurable ElevenLabs voice settings, env-based configuration, and MCP tool integration. The original repo is included as a git submodule at `packages/video-explainer/`.
- **[Weaviate](https://weaviate.io/)** -- the vector database powering the knowledge store. Eleven collections, hybrid search, and the [Weaviate Claude Code skill](https://github.com/weaviate/weaviate-claude-code-skill) that inspired the knowledge architecture.
- **[Google Gemini](https://ai.google.dev/)** (`google-genai` SDK) -- Gemini 3.1 Pro provides native video understanding, thinking mode, context caching, and the 2M token window that makes this possible.
- **[FastMCP](https://github.com/jlowin/fastmcp)** -- the MCP server framework. The composable sub-server pattern (`app.mount()`) keeps 24 tools organized across 7 namespaces.
- **[MLflow](https://mlflow.org/)** (`mlflow-tracing`) -- optional observability layer. Every Gemini call becomes a traceable span with token counts and latency.
- **[Pydantic](https://docs.pydantic.dev/)** -- schema validation for all tool inputs and outputs. Structured generation via `model_json_schema()`.
- **[Remotion](https://www.remotion.dev/)** -- React-based video rendering engine used by the explainer pipeline.
- **[ElevenLabs](https://elevenlabs.io/)** -- text-to-speech for voiceover generation with native word-level timestamps.
- **[Cohere](https://cohere.com/)** -- optional reranking in knowledge search for improved result relevance.
- **[Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)** -- powers parallel scene generation in `video-agent-mcp`.

## License

MIT
