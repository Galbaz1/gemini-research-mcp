# Open Issues: dotenv config loading not working in Claude Code MCP subprocess

## Status: UNRESOLVED

The dotenv auto-loader (`src/video_research_mcp/dotenv.py`) works correctly in all local tests but fails when Claude Code starts the MCP server as a subprocess.

## What was implemented

1. **`src/video_research_mcp/dotenv.py`** — Zero-dependency `.env` parser + loader. Reads `~/.config/video-research-mcp/.env` and injects vars into `os.environ` when they are missing or empty.
2. **`src/video_research_mcp/config.py`** — `get_config()` calls `load_dotenv()` before `ServerConfig.from_env()`.
3. **`bin/lib/config.js`** — Removed env passthroughs (`WEAVIATE_URL`, `WEAVIATE_API_KEY`, `YOUTUBE_API_KEY`, `GEMINI_API_KEY`) from `MCP_SERVERS` config. Added `ensureEnvFile()` to create template at install time.
4. **`bin/install.js`** — Calls `ensureEnvFile()` after `mergeConfig()`.
5. **`~/.config/video-research-mcp/.env`** — Created with real keys (chmod 600).
6. **All `.mcp.json` files cleaned** — Removed `env` blocks from project-level (`~/Desktop/video_analysis/.mcp.json`), global (`~/.claude/.mcp.json`), and repo-local (`.mcp.json`).

## What works

- **All 363 tests pass**, including 17 dotenv-specific tests.
- **Direct CLI test works perfectly:**
  ```
  env -u WEAVIATE_URL uv run --directory /path/to/repo python -c "
  from video_research_mcp.config import get_config
  cfg = get_config()
  print(cfg.weaviate_url)  # prints correct Weaviate Cloud URL
  "
  ```
- **Config file is found and parsed correctly** — verified with full diagnostic.
- **Package location is source tree** — confirmed `video_research_mcp.__file__` points to `/Users/fausto/code_projects_work/gemini-research-mcp/src/`.
- **`get_config()` source code has the `load_dotenv` call** — verified via `inspect.getsource()`.

## What doesn't work

When Claude Code starts the MCP server in `~/Desktop/video_analysis/`, `knowledge_stats` returns:
```
error: 1 validation error for ProtocolParams
host
  Value error, host must not be empty [type=value_error, input_value='', input_type=str]
```

This means `weaviate_url` is `""` in the running server, despite the dotenv loader being wired in.

## What was tried

### 1. Removed `env` blocks from all `.mcp.json` files
**Hypothesis:** `${WEAVIATE_URL}` in the env block resolves to `""` when the var isn't in the shell, setting `WEAVIATE_URL=""` in the process, which blocks the dotenv loader.

**Result:** Warning about missing env vars disappeared, but Weaviate still reports empty host.

**Files cleaned:**
- `~/.claude/.mcp.json`
- `~/Desktop/video_analysis/.mcp.json`
- `./mcp.json` (repo-local)

### 2. Made `load_dotenv` override empty-string env vars
**Hypothesis:** Something still sets `WEAVIATE_URL=""` (cached config, Claude Code internals).

**Change:** `if key not in os.environ` → `if not os.environ.get(key)` (treats `""` as unset).

**Result:** Tests pass. Not yet confirmed to fix the Claude Code subprocess issue.

### 3. Full Cmd+Q restart of Claude Code
**Hypothesis:** MCP server process was stale.

**Result:** Still doesn't work after full quit + relaunch.

### 4. Verified no shell profiles set WEAVIATE_URL
**Checked:** `~/.zshrc`, `~/.zprofile`, `~/.bashrc`, `~/.bash_profile` — none contain `WEAVIATE`.

### 5. Verified running process is from source
**Check:** `ps aux | grep video-research` shows `uv run --directory /path/to/source video-research-mcp`.

**Check:** `video_research_mcp.__file__` → points to source tree, not PyPI cache.

### 6. Verified bytecode cache is fresh
**Check:** `.pyc` timestamps match source file modification times.

### 7. Checked process environment
**Check:** `ps eww -p <pid>` shows `GEMINI_API_KEY` (from shell) but no `WEAVIATE_URL` — which is expected since `load_dotenv` modifies `os.environ` at runtime, not the process environment block.

## Remaining hypotheses

1. **Claude Code passes env vars not visible in `.mcp.json`** — Claude Code may have an internal mechanism that sets env vars on MCP subprocesses beyond what's in the `env` block. Could be caching from a previous config state.

2. **`uv run` environment isolation** — `uv run --directory` might sanitize or reset the environment in ways that affect `os.environ` modifications made by `load_dotenv()` at runtime.

3. **MCP stdio transport interference** — The MCP protocol uses stdin/stdout. FastMCP's startup sequence might initialize config before our `get_config()` is called, or there may be a separate config resolution path.

4. **Config singleton initialized elsewhere** — Some import-time side effect might create the config singleton before `get_config()` is called, bypassing the dotenv loader. (Partially ruled out: `inspect.getsource()` shows the correct code, and all `get_config()` calls in the codebase are inside functions, not at module level.)

5. **Multiple server instances** — Claude Code might merge server definitions from project + global configs in unexpected ways, or start the `uvx` (PyPI) version instead of the `uv run --directory` (source) version despite the project config.

## How to verify

Run this in a Claude Code session where Weaviate fails:
```
Use infra_configure to show current settings
```
Then check if `weaviate_url` is empty or populated.

Alternatively, add a temporary stderr diagnostic to `server.py`:
```python
import sys
from .config import get_config
cfg = get_config()
print(f"[DIAG] weaviate_url={cfg.weaviate_url!r}", file=sys.stderr)
```
Then check Claude Code's MCP server logs for the output.
