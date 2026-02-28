# Video Explainer MCP — Implementation Plan

A standalone MCP server wrapping [prajwal-y/video_explainer](https://github.com/prajwal-y/video_explainer) to create explainer videos from research output. Companion to `gemini-research-mcp` (extraction) — this server handles **synthesis**.

> **Source analysis**: `VIDEO_EXPLAINER_UPSTREAM_README.md` in this directory contains the upstream README.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Repository Structure](#2-repository-structure)
3. [Tool Inventory](#3-tool-inventory-15-tools-4-sub-servers)
4. [Core Abstraction: runner.py](#4-core-abstraction-runnerpy)
5. [Configuration](#5-configuration-configpy)
6. [Error Handling](#6-error-handling-errorspy)
7. [Project Scanner](#7-project-scanner-scannerpy)
8. [Background Jobs](#8-background-render-jobs-jobspy)
9. [Integration Flow](#9-integration-flow)
10. [Plugin Assets](#10-plugin-assets)
11. [Distribution Integration](#11-distribution-integration)
12. [Testing Strategy](#12-testing-strategy)
13. [Implementation Phases](#13-implementation-phases)
14. [Verification Checklist](#14-verification-checklist)
15. [Prerequisites](#15-prerequisites-for-end-users)
16. [Design Decisions](#16-design-decisions--trade-offs)

---

## 1. Architecture Overview

### What we're wrapping

`video_explainer` is a Python+Node.js CLI pipeline that transforms documents into explainer videos:

```
Document -> Parse -> Script -> TTS -> Storyboard -> Remotion -> Video
                      ^                                ^
                    Claude                         React/TSX
                 (script gen)                  (programmatic anim)
```

**Key architectural insight**: TTS happens *before* storyboard creation. The pipeline needs word-level timestamps from audio to sync visual animations frame-by-frame. Content determines timing, not the other way around.

**Tech stack**: Claude (`claude-code` provider) for script/scene generation, Remotion (React) for video rendering, ElevenLabs/Edge TTS for voiceover, MusicGen for background music, FFmpeg for final encoding.

### How the two servers relate

```
+----------------------------------+    +----------------------------------+
|     gemini-research-mcp          |    |     video-explainer-mcp          |
|     (22 tools -- extraction)     |    |     (15 tools -- synthesis)      |
|                                  |    |                                  |
|  video_analyze ------+           |    |  explainer_create                |
|  research_deep ------+           |    |  explainer_inject <--------------+
|  content_analyze ----+ markdown  |    |  explainer_generate              |
|  web_search ---------+    |      |    |  explainer_render_start          |
|                            |     |    |  explainer_render_poll           |
|                            v     |    |  ...                             |
|                       analysis   |--->|  projects/<id>/input/            |
|                       output     |    |  (filesystem = API contract)     |
+----------------------------------+    +----------------------------------+
```

### Key architectural decision

**Pure CLI wrapping** — no Python module imports from video_explainer.

The MCP server shells out to `python -m src.cli ...` for every operation. The project directory (`projects/<id>/`) is the shared state. This means:

- No dependency conflicts between the two packages
- video_explainer can be updated independently (just `git pull`)
- No Python version coupling (video_explainer uses 3.10+, this server uses 3.11+)
- Testing is simple — mock subprocess, not complex internal state
- Long-running operations (render = minutes) are naturally handled as background processes

---

## 2. Repository Structure

```
video-explainer-mcp/
|-- pyproject.toml                          # hatchling, fastmcp>=2.0, pydantic>=2.0
|-- CLAUDE.md                              # Project instructions for Claude Code
|-- LICENSE                                # MIT
|
|-- src/video_explainer_mcp/
|   |-- __init__.py                        # __version__
|   |-- server.py                          # FastMCP root + 4 sub-servers + main()
|   |-- config.py                          # ServerConfig singleton from env
|   |-- errors.py                          # ErrorCategory, SubprocessError, make_tool_error
|   |-- types.py                           # PipelineStep, RefinePhase, etc.
|   |-- runner.py                          # Async subprocess execution (core)
|   |-- scanner.py                         # Project dir inspection for step completion
|   |-- jobs.py                            # In-memory background render job tracking
|   |-- prereqs.py                         # Check python/node/ffmpeg availability
|   |-- models/
|   |   |-- __init__.py
|   |   |-- project.py                     # ProjectInfo, StepStatus
|   |   +-- pipeline.py                    # StepResult, RenderResult
|   +-- tools/
|       |-- __init__.py
|       |-- project.py                     # 4 tools: create, inject, status, list
|       |-- pipeline.py                    # 6 tools: generate, step, render, render_start, render_poll, short
|       |-- quality.py                     # 3 tools: refine, feedback, factcheck
|       +-- audio.py                       # 2 tools: sound, music
|
+-- tests/
    |-- conftest.py                        # mock_subprocess, mock_project_dir, clean_config
    |-- test_config.py
    |-- test_errors.py
    |-- test_runner.py
    |-- test_scanner.py
    |-- test_jobs.py
    |-- test_project_tools.py
    |-- test_pipeline_tools.py
    |-- test_quality_tools.py
    +-- test_audio_tools.py
```

### pyproject.toml outline

```toml
[project]
name = "video-explainer-mcp"
version = "0.1.0"
description = "MCP server for generating explainer videos via video_explainer CLI"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = [
    "fastmcp>=2.0",
    "pydantic>=2.0",
]

[project.scripts]
video-explainer-mcp = "video_explainer_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/video_explainer_mcp"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "ruff>=0.9"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100
```

Minimal dependencies — only `fastmcp` and `pydantic`. Everything else lives in video_explainer.

---

## 3. Tool Inventory (15 tools, 4 sub-servers)

### Sub-server: `project` (4 tools)

| Tool | Wraps CLI | ToolAnnotations | Purpose |
|------|-----------|-----------------|---------|
| `explainer_create` | `create <id>` | write, not destructive | Create project with config |
| `explainer_inject` | (direct file write) | write, not destructive | Write content into `input/` -- bridge from gemini-research |
| `explainer_status` | `info <id>` + dir scan | readOnly | Check pipeline progress |
| `explainer_list` | `list` | readOnly | List all projects |

#### explainer_create

```python
@project_server.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                idempotentHint=False, openWorldHint=False)
)
async def explainer_create(
    project_id: Annotated[str, Field(
        min_length=1, max_length=64, pattern=r'^[a-z0-9-]+$',
        description="Project ID (lowercase alphanumeric + hyphens)"
    )],
    title: Annotated[str, Field(
        max_length=200, description="Human-readable project title"
    )] = "",
    target_duration_seconds: Annotated[int, Field(
        ge=30, le=600, description="Target video duration in seconds"
    )] = 180,
) -> dict:
    """Create a new video explainer project.

    Initializes a project directory with config.json and subdirectories
    for each pipeline step (input, script, narration, scenes, etc.).

    Args:
        project_id: Unique slug for the project.
        title: Display title for the video.
        target_duration_seconds: Target length of final video.

    Returns:
        Dict with project_id, project_dir, status, and config.
    """
```

Returns: `{"project_id": str, "project_dir": str, "status": "created", "config": dict}`

#### explainer_inject (the key integration tool)

```python
@project_server.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                idempotentHint=False, openWorldHint=False)
)
async def explainer_inject(
    project_id: Annotated[str, Field(description="Target project ID")],
    content: Annotated[str, Field(
        min_length=1,
        description="Markdown content to write as input document"
    )],
    filename: Annotated[str, Field(
        description="Filename for the input (e.g. 'research.md')"
    )] = "content.md",
) -> dict:
    """Write source content into a project's input/ directory.

    This is the bridge between gemini-research-mcp analysis output and
    video_explainer's pipeline. Accepts markdown content (from research_deep,
    content_analyze, etc.) and writes it as an input document.

    Args:
        project_id: Target project to inject content into.
        content: Markdown text to write.
        filename: Name for the file in input/.

    Returns:
        Dict with project_id, file_path, bytes_written, and status.
    """
```

Returns: `{"project_id": str, "file_path": str, "bytes_written": int, "status": "injected"}`

#### explainer_status

Returns per-step completion:
```json
{
    "project_id": "quantum",
    "exists": true,
    "steps": {
        "input":      {"completed": true,  "file_count": 2, "last_modified": "2026-02-28T10:00:00"},
        "script":     {"completed": true,  "file_count": 1, "last_modified": "2026-02-28T10:01:00"},
        "narration":  {"completed": false, "file_count": 0, "last_modified": null},
        "scenes":     {"completed": false, "file_count": 0, "last_modified": null},
        "voiceover":  {"completed": false, "file_count": 0, "last_modified": null},
        "storyboard": {"completed": false, "file_count": 0, "last_modified": null},
        "render":     {"completed": false, "file_count": 0, "last_modified": null},
        "music":      {"completed": false, "file_count": 0, "last_modified": null},
        "sfx":        {"completed": false, "file_count": 0, "last_modified": null},
        "short":      {"completed": false, "file_count": 0, "last_modified": null}
    },
    "config": {"id": "quantum", "title": "Quantum Computing"},
    "input_files": ["research.md", "source_video.md"],
    "output_files": []
}
```

#### explainer_list

Returns: `{"projects": [{"project_id": str, "title": str, "completed_steps": int, "total_steps": int, "has_output": bool}], "total": int}`

### Sub-server: `pipeline` (6 tools)

| Tool | Wraps CLI | Purpose |
|------|-----------|---------|
| `explainer_generate` | `generate <id> [--from X --to Y --force --mock]` | Full or partial pipeline |
| `explainer_step` | `script/narration/scenes/voiceover/storyboard <id>` | Single pipeline step |
| `explainer_render` | `render <id> [-r preset --fast]` | Blocking render (for previews) |
| `explainer_render_start` | `render <id>` (background) | Async render, returns job ID |
| `explainer_render_poll` | (reads job store) | Check background render |
| `explainer_short` | `short generate <id>` | Shorts pipeline |

#### explainer_generate

```python
async def explainer_generate(
    project_id: Annotated[str, Field(description="Project ID")],
    from_step: Annotated[PipelineStep | None, Field(
        description="Start from this step (inclusive)"
    )] = None,
    to_step: Annotated[PipelineStep | None, Field(
        description="Stop at this step (inclusive)"
    )] = None,
    force: Annotated[bool, Field(description="Regenerate even if outputs exist")] = False,
    mock: Annotated[bool, Field(description="Use mock LLM/TTS (for testing)")] = False,
) -> dict:
```

Where `PipelineStep = Literal["script", "narration", "scenes", "voiceover", "storyboard"]`

Returns: `{"project_id": str, "steps_run": list[str], "status": "completed"|"failed", "duration_seconds": float, "error": str|None, "output_path": str|None}`

#### explainer_render (blocking -- for quick previews)

```python
async def explainer_render(
    project_id: Annotated[str, Field(description="Project ID")],
    resolution: Annotated[RenderResolution | None, Field(
        description="Resolution preset (4k, 1440p, 1080p, 720p, 480p)"
    )] = None,
    short: Annotated[bool, Field(description="Render short format")] = False,
    fast: Annotated[bool, Field(description="Faster encoding, lower quality")] = False,
    concurrency: Annotated[int, Field(ge=1, le=16, description="Render threads")] = 4,
) -> dict:
```

Where `RenderResolution = Literal["4k", "1440p", "1080p", "720p", "480p"]`

#### explainer_render_start / explainer_render_poll (async pattern)

Background render pattern for long-running 1080p+ renders:

```
1. explainer_render_start(project_id) -> {"job_id": "abc123", "status": "started"}
2. (wait...)
3. explainer_render_poll(job_id="abc123") -> {"status": "running", "elapsed_seconds": 120}
4. (wait...)
5. explainer_render_poll(job_id="abc123") -> {"status": "completed", "output_path": "..."}
```

### Sub-server: `quality` (3 tools)

| Tool | Wraps CLI | Purpose |
|------|-----------|---------|
| `explainer_refine` | `refine <id> --phase <phase>` | 4-phase quality improvement |
| `explainer_feedback` | `feedback <id> add "<text>"` | Natural language feedback |
| `explainer_factcheck` | `factcheck <id>` | Verify accuracy against sources |

Where `RefinePhase = Literal["analyze", "script", "visual-cue", "visual"]`

### Sub-server: `audio` (2 tools)

| Tool | Wraps CLI | Purpose |
|------|-----------|---------|
| `explainer_sound` | `sound <id> analyze/generate` | SFX planning + generation |
| `explainer_music` | `music <id> generate` | AI background music (MusicGen) |

Where `SoundAction = Literal["analyze", "generate"]`

---

## 4. Core Abstraction: `runner.py`

Every tool delegates CLI execution to this module.

### API

```python
async def run_cli(*args: str, timeout: int | None = None) -> SubprocessResult:
    """Run: {python_command} -m src.cli {args} from explainer_path."""
```

### Behavior

- Uses `asyncio.create_subprocess_exec` (not shell=True) -- no injection risk
- Captures stdout/stderr via PIPE
- Applies configurable timeout via `asyncio.wait_for`
- On timeout: SIGTERM, wait 5s, then SIGKILL
- Returns `SubprocessResult(stdout, stderr, returncode, duration_seconds, command)`
- Raises `SubprocessError` on non-zero exit (caught by tools via `make_tool_error`)
- Working directory is always `explainer_path` -- where `src.cli` lives

### SubprocessResult

```python
@dataclass(frozen=True)
class SubprocessResult:
    stdout: str
    stderr: str
    returncode: int
    duration_seconds: float
    command: list[str]
```

### Error flow

```
run_cli("generate", "my-project")
  |
  +-- success -> SubprocessResult
  |
  +-- non-zero exit -> SubprocessError
  |     |
  |     +-- caught by tool -> make_tool_error(exc)
  |           |
  |           +-- categorize_error(exc) -> (STEP_FAILED, "hint...")
  |           |
  |           +-- return {"error": ..., "category": ..., "hint": ..., "retryable": ...}
  |
  +-- timeout -> asyncio.TimeoutError
  |     |
  |     +-- SIGTERM -> wait 5s -> SIGKILL
  |     +-- caught by tool -> make_tool_error(exc) -> SUBPROCESS_TIMEOUT
  |
  +-- missing path -> FileNotFoundError
        |
        +-- caught by tool -> make_tool_error(exc) -> EXPLAINER_NOT_FOUND
```

---

## 5. Configuration (`config.py`)

Singleton pattern matching `gemini-research-mcp/src/video_research_mcp/config.py`.

```python
class ServerConfig(BaseModel):
    """Runtime configuration resolved from environment."""

    # video_explainer location (required)
    explainer_path: str = Field(default="")

    # Override projects directory (default: {explainer_path}/projects)
    projects_path: str = Field(default="")

    # LLM provider for video_explainer
    llm_provider: str = Field(default="claude-code")
    llm_model: str = Field(default="claude-sonnet-4-20250514")

    # TTS provider
    tts_provider: str = Field(default="mock")
    elevenlabs_api_key: str = Field(default="")

    # Video defaults
    video_width: int = Field(default=1920)
    video_height: int = Field(default=1080)
    video_fps: int = Field(default=30)

    # Subprocess limits
    subprocess_timeout_seconds: int = Field(default=600)   # 10 min general
    render_timeout_seconds: int = Field(default=1800)       # 30 min for renders

    # Executables
    python_command: str = Field(default="python")

    @classmethod
    def from_env(cls) -> ServerConfig: ...
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPLAINER_PATH` | `""` (required) | Path to cloned video_explainer repo |
| `EXPLAINER_PROJECTS_PATH` | `""` | Override projects dir |
| `EXPLAINER_LLM_PROVIDER` | `claude-code` | LLM provider |
| `EXPLAINER_TTS_PROVIDER` | `mock` | TTS provider (`mock`, `elevenlabs`, `edge`) |
| `ELEVENLABS_API_KEY` | `""` | ElevenLabs API key |
| `EXPLAINER_TIMEOUT` | `600` | General subprocess timeout (seconds) |
| `EXPLAINER_RENDER_TIMEOUT` | `1800` | Render timeout (30 min) |
| `EXPLAINER_PYTHON` | `python` | Python executable |

---

## 6. Error Handling (`errors.py`)

Follows `gemini-research-mcp/src/video_research_mcp/errors.py` pattern exactly: tools never raise, always return `make_tool_error(exc)`.

### Error categories

```python
class ErrorCategory(str, Enum):
    # Prerequisites
    EXPLAINER_NOT_FOUND = "EXPLAINER_NOT_FOUND"
    PYTHON_NOT_FOUND = "PYTHON_NOT_FOUND"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    FFMPEG_NOT_FOUND = "FFMPEG_NOT_FOUND"
    REMOTION_NOT_INSTALLED = "REMOTION_NOT_INSTALLED"

    # Project errors
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_EXISTS = "PROJECT_EXISTS"
    PROJECT_INCOMPLETE = "PROJECT_INCOMPLETE"

    # Subprocess errors
    SUBPROCESS_TIMEOUT = "SUBPROCESS_TIMEOUT"
    SUBPROCESS_FAILED = "SUBPROCESS_FAILED"
    SUBPROCESS_CRASHED = "SUBPROCESS_CRASHED"

    # Pipeline errors
    STEP_FAILED = "STEP_FAILED"
    RENDER_FAILED = "RENDER_FAILED"
    TTS_FAILED = "TTS_FAILED"

    # Job errors
    JOB_NOT_FOUND = "JOB_NOT_FOUND"

    UNKNOWN = "UNKNOWN"
```

### Categorization from subprocess output

| Pattern in stderr | Category | Hint |
|-------------------|----------|------|
| FileNotFoundError + explainer path | `EXPLAINER_NOT_FOUND` | "Set EXPLAINER_PATH to the video_explainer repo root" |
| "project" + "not found" | `PROJECT_NOT_FOUND` | "Create with explainer_create first" |
| "npm" or "node_modules" | `REMOTION_NOT_INSTALLED` | "Run: cd remotion && npm install" |
| asyncio.TimeoutError | `SUBPROCESS_TIMEOUT` | "Use explainer_render_start for background execution" |
| returncode < 0 (signal) | `SUBPROCESS_CRASHED` | "Process killed by signal. Check system resources" |
| Non-zero exit | `SUBPROCESS_FAILED` | First 500 chars of stderr |

### SubprocessError

```python
class SubprocessError(Exception):
    """Wraps a failed subprocess call with structured context."""

    def __init__(self, command: list[str], returncode: int, stdout: str, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command failed (exit {returncode}): {' '.join(command)}")
```

---

## 7. Project Scanner (`scanner.py`)

Inspects the project directory to determine step completion **without running CLI commands**. Used by `explainer_status`.

### Completion detection rules

| Step | Directory | Completed when |
|------|-----------|---------------|
| input | `input/` | Has `.md` or `.pdf` files |
| script | `script/` | `script.json` exists |
| narration | `narration/` | `narrations.json` exists |
| scenes | `scenes/` | `*.tsx` files exist |
| voiceover | `voiceover/` | `*.mp3` files exist |
| storyboard | `storyboard/` | `storyboard.json` exists |
| render | `output/` | `*.mp4` files exist |
| music | `music/` | `background.mp3` exists |
| sfx | `sfx/` | `*.wav` files exist |
| short | `short/output/` | `*.mp4` files exist |

### StepStatus model

```python
class StepStatus(BaseModel):
    """Completion status for a single pipeline step."""
    completed: bool = False
    file_count: int = 0
    last_modified: str | None = None  # ISO 8601 timestamp of newest file
```

---

## 8. Background Render Jobs (`jobs.py`)

Renders can take 10+ minutes -- exceeding typical MCP request timeouts. Solution: start/poll pattern.

```python
@dataclass
class RenderJob:
    job_id: str           # uuid4 hex, 12 chars
    project_id: str
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    completed_at: datetime | None
    output_path: str | None
    error: str | None
```

### How it works

1. `explainer_render_start` calls `create_job()`, spawns `asyncio.create_task` with the render subprocess
2. Returns immediately with `{"job_id": "abc123", "status": "started"}`
3. The background task updates the job store on completion or failure
4. `explainer_render_poll` reads the job store and returns current status
5. Jobs are in-memory -- they survive until server restarts

---

## 9. Integration Flow

### End-to-end workflow

```
User: "Make an explainer video about quantum computing"

1. /ve:explain-video "quantum computing"
   |
   |  +--- gemini-research-mcp ---+
   +--| research_deep(topic=...)  |
   +--| web_search(query=...)     |
   |  +---------------------------+
   |
   |  (Claude synthesizes findings into structured markdown)
   |
   |  +--- video-explainer-mcp --------------------+
   +--| explainer_create(project_id="quantum")     |
   +--| explainer_inject(project_id="quantum",     |
   |  |     content=<markdown>, filename="res.md") |
   +--| explainer_generate(project_id="quantum")   |
   |  |   script -> narration -> scenes ->         |
   |  |   voiceover -> storyboard                  |
   +--| explainer_render_start(project_id=...)     |
   |  |   Returns job_id, renders in background    |
   +--| explainer_render_poll(job_id=...)           |
      |   Returns output path when done            |
      +--------------------------------------------+
```

### Content injection examples

**From research_deep:**
```python
explainer_inject(
    project_id="quantum",
    content="# Quantum Computing\n\n## Overview\n...",
    filename="research.md"
)
```

**Multiple sources into one project:**
```python
explainer_inject(project_id="quantum", content=research_md, filename="research.md")
explainer_inject(project_id="quantum", content=video_md, filename="video_notes.md")
explainer_inject(project_id="quantum", content=paper_md, filename="arxiv_paper.md")
# All three land in projects/quantum/input/
# video_explainer parses all of them during script generation
```

---

## 10. Plugin Assets

Distributed via the existing `gemini-research-mcp` npm installer. All assets live in the gemini-research-mcp repo and get copied to `~/.claude/` on install.

### Commands (3, under /ve: namespace)

#### /ve:explainer -- Full workflow

```yaml
---
description: Create an explainer video from content
argument-hint: <project-id or "from <source>">
allowed-tools: mcp__video-explainer__explainer_create, mcp__video-explainer__explainer_inject,
  mcp__video-explainer__explainer_generate, mcp__video-explainer__explainer_status,
  mcp__video-explainer__explainer_render_start, mcp__video-explainer__explainer_render_poll,
  mcp__video-explainer__explainer_step, mcp__video-explainer__explainer_refine,
  mcp__video-explainer__explainer_feedback, Read, Write, Glob
model: sonnet
---
```

Phases: Setup -> Inject -> Generate -> Review -> Render -> Extras (sound, music, shorts)

#### /ve:explain-video -- Bridge workflow

```yaml
---
description: Quick explainer video from gemini-research analysis
argument-hint: <path-to-analysis.md or topic>
allowed-tools: [video-explainer tools + gemini-research tools]
model: sonnet
---
```

Uses **both** MCP servers: research with gemini-research, create with video-explainer.

#### /ve:explain-status -- Status check

```yaml
---
description: Check video explainer project status and progress
argument-hint: "[project-id]"
allowed-tools: mcp__video-explainer__explainer_status, mcp__video-explainer__explainer_list
model: haiku
---
```

### Skill (1)

**`skills/video-explainer/SKILL.md`** -- Tool usage guide covering:
- Tool selection table (which tool for what)
- Complete API reference for all 15 tools
- Pipeline step order: `script -> narration -> scenes -> voiceover -> storyboard -> render`
- Background render pattern (start/poll)
- Content injection from gemini-research-mcp
- Error handling (check for "error" key)
- Workflow patterns and refinement cycles

### Agents (2)

**`agents/video-producer.md`** -- Full pipeline orchestrator with all 15 explainer tools. Color: orange.

**`agents/content-to-video.md`** -- Bridge agent with both gemini-research analysis tools and explainer injection tools. Reads `memory/gr/` analysis files. Color: cyan.

---

## 11. Distribution Integration

Extend the **existing** `gemini-research-mcp` npm installer -- no separate npm package.

### Changes to bin/lib/copy.js

Add to FILE_MAP:
```js
// Video Explainer commands (under /ve: namespace)
'commands/explainer.md':       'commands/ve/explainer.md',
'commands/explain-video.md':   'commands/ve/explain-video.md',
'commands/explain-status.md':  'commands/ve/explain-status.md',

// Video Explainer skill
'skills/video-explainer/SKILL.md': 'skills/video-explainer/SKILL.md',

// Video Explainer agents
'agents/video-producer.md':    'agents/video-producer.md',
'agents/content-to-video.md':  'agents/content-to-video.md',
```

Add to CLEANUP_DIRS:
```js
'skills/video-explainer',
'commands/ve',
```

### Changes to bin/lib/config.js

Add to MCP_SERVERS:
```js
'video-explainer': {
    command: 'uvx',
    args: ['video-explainer-mcp'],
    env: {
        EXPLAINER_PATH: '${EXPLAINER_PATH}',
        ELEVENLABS_API_KEY: '${ELEVENLABS_API_KEY}',
    },
},
```

### Files changed in gemini-research-mcp

| File | Change |
|------|--------|
| `bin/lib/copy.js` | Add 6 entries to FILE_MAP, 2 to CLEANUP_DIRS |
| `bin/lib/config.js` | Add `video-explainer` to MCP_SERVERS |
| `commands/explainer.md` | New file |
| `commands/explain-video.md` | New file |
| `commands/explain-status.md` | New file |
| `skills/video-explainer/SKILL.md` | New file |
| `agents/video-producer.md` | New file |
| `agents/content-to-video.md` | New file |

---

## 12. Testing Strategy

All tests mock subprocess -- no real CLI execution.

### Key fixtures (conftest.py)

- **`mock_subprocess`**: Configurable AsyncMock process with stdout/stderr/returncode
- **`mock_project_dir`**: Temp directory with video_explainer project structure
- **`clean_config`**: Autouse, sets `EXPLAINER_PATH=/fake/path`, resets singleton

### Test coverage

| File | What it tests | Count |
|------|---------------|-------|
| `test_config.py` | Env var parsing, defaults, validation, singleton | ~8 |
| `test_errors.py` | Category mapping from stderr, hint generation | ~10 |
| `test_runner.py` | Command construction, timeout, signal handling | ~12 |
| `test_scanner.py` | Directory scanning, step detection, missing project | ~12 |
| `test_jobs.py` | Job lifecycle: create, poll, complete, fail | ~8 |
| `test_project_tools.py` | create, inject, status, list | ~12 |
| `test_pipeline_tools.py` | generate, step, render, render_start/poll, short | ~15 |
| `test_quality_tools.py` | refine (phases), feedback, factcheck | ~8 |
| `test_audio_tools.py` | sound (analyze/generate), music | ~5 |
| **Total** | | **~90** |

All unit-level, async (`asyncio_mode=auto`), no real subprocess calls.

---

## 13. Implementation Phases

### Phase 1: Foundation

| # | File | Description |
|---|------|-------------|
| 1 | `pyproject.toml` | Init repo, directory structure, `__init__.py` |
| 2 | `config.py` | ServerConfig + env vars + singleton |
| 3 | `errors.py` | ErrorCategory, SubprocessError, make_tool_error |
| 4 | `types.py` | PipelineStep, RefinePhase, SoundAction, RenderResolution |
| 5 | `models/` | Pydantic return models |
| 6 | Tests | `test_config.py`, `test_errors.py` |

### Phase 2: Core Infrastructure

| # | File | Description |
|---|------|-------------|
| 7 | `runner.py` | Async subprocess execution, timeout, signals |
| 8 | `scanner.py` | Project directory scanning |
| 9 | `jobs.py` | Background render job tracking |
| 10 | `prereqs.py` | Prerequisite checks |
| 11 | `conftest.py` | Shared test fixtures |
| 12 | Tests | `test_runner.py`, `test_scanner.py`, `test_jobs.py` |

### Phase 3: Tools

| # | File | Description |
|---|------|-------------|
| 13 | `tools/project.py` | 4 project management tools |
| 14 | `tools/pipeline.py` | 6 pipeline execution tools |
| 15 | `tools/quality.py` | 3 quality assurance tools |
| 16 | `tools/audio.py` | 2 audio tools |
| 17 | `server.py` | Root server + sub-server mounting + main() |
| 18 | Tests | All tool test files |

### Phase 4: Plugin Assets

| # | File | Description |
|---|------|-------------|
| 19 | `commands/*.md` | 3 command files |
| 20 | `skills/*/SKILL.md` | Tool usage guide |
| 21 | `agents/*.md` | 2 agent files |

### Phase 5: Distribution

| # | File | Description |
|---|------|-------------|
| 22 | `bin/lib/copy.js` | FILE_MAP + CLEANUP_DIRS |
| 23 | `bin/lib/config.js` | MCP_SERVERS entry |
| 24 | -- | End-to-end test |

---

## 14. Verification Checklist

### Server

- [ ] `uv pip install -e ".[dev]"` succeeds
- [ ] `uv run pytest tests/ -v` -- all ~90 tests pass
- [ ] `EXPLAINER_PATH=... uv run video-explainer-mcp` -- server starts
- [ ] Server registers 15 tools across 4 sub-servers

### Tools

- [ ] `explainer_list()` -- returns empty project list
- [ ] `explainer_create(project_id="test")` -- creates project
- [ ] `explainer_inject(project_id="test", content="# Test")` -- writes file
- [ ] `explainer_status(project_id="test")` -- input completed, rest pending
- [ ] `explainer_generate(project_id="test", to_step="script")` -- generates script
- [ ] `explainer_render_start(project_id="test")` -- returns job ID
- [ ] `explainer_render_poll(job_id="...")` -- shows status
- [ ] `explainer_status(project_id="nonexistent")` -- returns error dict

### Plugin

- [ ] `node bin/install.js --global --check` shows 6 new files
- [ ] `node bin/install.js --global` copies files + registers MCP server
- [ ] `~/.claude/commands/ve/` has 3 files
- [ ] `~/.claude/skills/video-explainer/` has SKILL.md
- [ ] `~/.claude/.mcp.json` has `video-explainer` entry

### End-to-end

- [ ] `/ve:explain-status` lists projects
- [ ] `/ve:explainer my-video` creates + runs pipeline
- [ ] `/ve:explain-video "topic"` researches + creates + generates

---

## 15. Prerequisites for End Users

1. **Clone video_explainer**: `git clone https://github.com/prajwal-y/video_explainer`
2. **Install Python deps**: `cd video_explainer && pip install -e .`
3. **Install Remotion deps**: `cd remotion && npm install`
4. **Set env var**: `export EXPLAINER_PATH=/path/to/video_explainer`
5. **FFmpeg**: `brew install ffmpeg`
6. **Node.js 20+**: `nvm install 20 && nvm use 20`
7. **Optional**: `ELEVENLABS_API_KEY` for real TTS (mock works without)
8. **Optional**: `ANTHROPIC_API_KEY` if using `anthropic` LLM provider

---

## 16. Design Decisions & Trade-offs

### Why CLI wrapping instead of module imports

| Factor | CLI wrapping | Module import |
|--------|-------------|---------------|
| Dependency coupling | None | Heavy (torch, numpy, edge-tts) |
| Version conflicts | Impossible | Likely (pydantic, etc.) |
| Update path | `git pull` | Re-vendor + test |
| Long operations | Natural background process | Blocks event loop |
| Testing | Mock subprocess | Mock complex internals |
| Debugging | Read stderr | Foreign stack traces |

### Why start/poll instead of streaming for render

MCP does not support long-lived streaming responses. Renders take 10-15 minutes. The start/poll pattern is the standard async job approach within MCP's request/response model.

### Why `explainer_inject` instead of Claude writing files

- Validates project exists before writing
- Uses correct project path from config
- Makes intent explicit in tool logs
- Enables clean skill documentation

### Why separate blocking and async render

Short renders (preview, 480p) finish in under a minute -- blocking is fine. Full 1080p+ renders need the async pattern. Having both gives Claude flexibility to choose.

### Why /ve: namespace (not /gr:)

- Clear visual distinction from /gr: (Gemini Research)
- Separate concerns: different servers, different namespaces
- User clarity: /ve:explainer = video creation

### Why distribute via existing npm installer

- Single `npx video-research-mcp@latest` installs everything
- FILE_MAP handles multiple namespaces cleanly
- Manifest tracking handles per-file upgrades
- Complementary products benefit from bundling
