# Plugin Distribution — Two-Package Architecture

> How the Claude Code plugin is built, distributed, and discovered.

## Overview

`video-research-mcp` ships as **two packages with the same name** on different registries:

| Package | Registry | Purpose | Runs when |
|---------|----------|---------|-----------|
| `video-research-mcp` | **PyPI** | MCP server (Python runtime) | Claude Code starts a session — `uvx` downloads and runs it |
| `video-research-mcp` | **npm** | Plugin installer (Node.js script) | User runs `npx video-research-mcp@latest` once to install |

The npm package contains zero Python code. The PyPI package contains zero JavaScript. They share a name for brand consistency.

## npm Package — The Installer

### What it does

`bin/install.js` copies 17 markdown files into `~/.claude/` (global) or `.claude/` (local), then writes MCP server config to `.mcp.json`. That's it — no runtime, no daemon.

```
npx video-research-mcp@latest
        │
        ├── Copies 8 commands  → ~/.claude/commands/gr/
        ├── Copies 6 skill files → ~/.claude/skills/
        ├── Copies 4 agents    → ~/.claude/agents/
        ├── Writes .mcp.json   → MCP server registration
        └── Writes manifest    → for upgrades/uninstall
```

### Key files

| File | Role |
|------|------|
| `bin/install.js` | CLI entry point — parses flags, orchestrates install/uninstall |
| `bin/lib/copy.js` | `FILE_MAP` (source→dest mapping), `CLEANUP_DIRS`, copy/remove helpers |
| `bin/lib/manifest.js` | SHA-256 hashing, upgrade diffing, user-modification detection |
| `bin/lib/config.js` | `.mcp.json` merge — registers `video-research` + `playwright` servers |
| `bin/lib/ui.js` | Terminal output formatting |
| `package.json` | npm metadata — `"bin"` points to `install.js`, `"files"` limits what gets published |

### FILE_MAP — the central registry

Every file distributed by the plugin must be listed in `bin/lib/copy.js`:

```js
const FILE_MAP = {
  // Commands → /gr:* slash commands
  'commands/video.md':      'commands/gr/video.md',
  'commands/video-chat.md': 'commands/gr/video-chat.md',
  'commands/research.md':   'commands/gr/research.md',
  'commands/analyze.md':    'commands/gr/analyze.md',
  'commands/search.md':     'commands/gr/search.md',
  'commands/recall.md':     'commands/gr/recall.md',
  'commands/models.md':     'commands/gr/models.md',
  'commands/doctor.md':     'commands/gr/doctor.md',

  // Skills → context injection
  'skills/video-research/SKILL.md':                              'skills/video-research/SKILL.md',
  'skills/gemini-visualize/SKILL.md':                             'skills/gemini-visualize/SKILL.md',
  'skills/gemini-visualize/templates/video-concept-map.md':       'skills/gemini-visualize/templates/video-concept-map.md',
  'skills/gemini-visualize/templates/research-evidence-net.md':   'skills/gemini-visualize/templates/research-evidence-net.md',
  'skills/gemini-visualize/templates/content-knowledge-graph.md': 'skills/gemini-visualize/templates/content-knowledge-graph.md',
  'skills/weaviate-setup/SKILL.md':                               'skills/weaviate-setup/SKILL.md',

  // Agents → sub-agents
  'agents/researcher.md':      'agents/researcher.md',
  'agents/video-analyst.md':   'agents/video-analyst.md',
  'agents/visualizer.md':      'agents/visualizer.md',
  'agents/comment-analyst.md': 'agents/comment-analyst.md',
};
```

**To add a new command/skill/agent:** create the markdown file, add its entry to `FILE_MAP`, add its parent directory to `CLEANUP_DIRS` if new, then run `node bin/install.js --global`.

### Manifest tracking

The installer writes `~/.claude/gr-file-manifest.json` containing SHA-256 hashes of every installed file. This enables:

- **Upgrade detection**: only overwrite files that haven't been user-modified
- **User modification protection**: if the user edited a skill, `--force` is required to overwrite
- **Clean uninstall**: only remove files whose hash matches the manifest
- **Obsolete file cleanup**: when a file is removed from FILE_MAP, it's deleted on upgrade

### MCP config merge

`bin/lib/config.js` writes two MCP server entries to `.mcp.json`:

```json
{
  "mcpServers": {
    "video-research": {
      "command": "uvx",
      "args": ["video-research-mcp"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--caps=vision,pdf"]
    }
  }
}
```

Config location: `~/.claude/.mcp.json` (global) or `./.mcp.json` (local, project root).

---

## PyPI Package — The Server

The Python package (defined in `pyproject.toml`) is the actual MCP server. Users never install it manually — `uvx` handles it when Claude Code reads `.mcp.json`.

The server exposes 22 tools across 7 sub-servers. See the Architecture section in the root `CLAUDE.md`.

---

## How Claude Code Discovers Plugin Assets

Claude Code scans two directory trees at session start:

```
~/.claude/                        ← global (all projects)
  commands/<namespace>/<name>.md  ← slash commands
  skills/<name>/SKILL.md          ← skills
  agents/<name>.md                ← sub-agents

.claude/                          ← local (current project only)
  commands/...
  skills/...
  agents/...
```

### Commands → Slash Commands

A file at `commands/gr/video.md` becomes the slash command `/gr:video`.

Structure:
```markdown
---
description: "Short description shown in autocomplete"
argument-hint: "<url or path>"
allowed-tools: [video_analyze, video_metadata, Write, Read]
model: sonnet
---

Your prompt template here. Use $ARGUMENTS for user input.
```

| Frontmatter | Purpose |
|-------------|---------|
| `description` | Shown in command picker / autocomplete |
| `argument-hint` | Placeholder text after the command name |
| `allowed-tools` | Restricts which MCP tools + built-in tools the command can use |
| `model` | Which Claude model runs the command (sonnet, haiku, opus) |

When a user types `/gr:video https://youtube.com/...`:
1. Claude Code loads `commands/gr/video.md`
2. Replaces `$ARGUMENTS` with the user's input
3. Restricts tool usage to `allowed-tools`
4. Executes with the specified `model`

### Skills → Context Injection

A `skills/<name>/SKILL.md` provides domain knowledge that Claude loads when relevant. This is the **anti-hallucination mechanism** — it overrides the model's training knowledge with correct, project-specific API syntax.

```markdown
---
name: video-research
description: "Teaches Claude how to use the 22 video-research tools"
---

## Tool Signatures
- `video_analyze(url, instruction, thinking_level)` ...

## Workflow Patterns
1. Start with research_plan for complex topics ...

## Anti-patterns
- Never set alpha=1.0 for exact keyword matches ...
```

Claude Code loads the skill when its `description` matches the user's intent. The full SKILL.md content is injected into the system prompt before Claude responds.

Skills can have sub-files (like `skills/gemini-visualize/templates/*.md`) that are referenced from the main SKILL.md.

### Agents → Sub-agents

An `agents/<name>.md` defines a specialized agent that can be launched via the `Task` tool:

```markdown
---
name: researcher
color: blue
model: sonnet
tools: [research_plan, web_search, research_deep, Write, Read]
---

You are a multi-phase research specialist...
```

These run as background or foreground processes with their own tool restrictions and system prompts.

---

## Current Plugin Inventory

### Commands (8)

| File | Slash Command | Tools | Model |
|------|---------------|-------|-------|
| `commands/video.md` | `/gr:video` | video_analyze, video_batch, video_session, video_metadata, video_playlist | sonnet |
| `commands/video-chat.md` | `/gr:video-chat` | video_create_session, video_continue_session | sonnet |
| `commands/research.md` | `/gr:research` | web_search, research_deep, research_plan, research_assess_evidence | sonnet |
| `commands/analyze.md` | `/gr:analyze` | content_analyze, content_extract | sonnet |
| `commands/search.md` | `/gr:search` | web_search | sonnet |
| `commands/recall.md` | `/gr:recall` | Glob, Grep, Read (filesystem only) | sonnet |
| `commands/models.md` | `/gr:models` | infra_configure | haiku |
| `commands/doctor.md` | `/gr:doctor` (`quick` compact, `full` detailed) | infra_configure, video_metadata, knowledge_stats, Read/Glob/Bash | haiku |

### Skills (3)

| Skill | Purpose |
|-------|---------|
| `video-research` | Tool signatures, workflows, caching for 22 tools |
| `gemini-visualize` | HTML visualization generation + 3 templates |
| `weaviate-setup` | Interactive onboarding wizard for Weaviate connection |

### Agents (4)

| Agent | Model | Purpose |
|-------|-------|---------|
| `researcher` | sonnet | Multi-phase research with evidence tiers |
| `video-analyst` | sonnet | Video analysis and Q&A sessions |
| `visualizer` | sonnet | Background HTML visualization + screenshot |
| `comment-analyst` | haiku | Background YouTube comment analysis |

---

## Complete Flow

```
USER: npx video-research-mcp@latest
         │
         ▼
    bin/install.js (Node.js)
         │
         ├── Copy 17 markdown files to ~/.claude/
         ├── Write .mcp.json (register MCP servers)
         └── Write manifest (for future upgrades)

USER: starts Claude Code
         │
         ├── Read .mcp.json
         │    └── Start: uvx video-research-mcp  ← Python server from PyPI
         │
         ├── Scan ~/.claude/commands/
         │    └── Register /gr:video, /gr:research, etc.
         │
         ├── Scan ~/.claude/skills/
         │    └── Index skill descriptions for context matching
         │
         └── Scan ~/.claude/agents/
              └── Register researcher, video-analyst, etc.

USER: /gr:research "quantum computing"
         │
         ├── Load commands/gr/research.md (prompt template)
         ├── Load skills/video-research/SKILL.md (context)
         ├── Call research_plan → research_deep via MCP server
         ├── Server calls Gemini API
         ├── Server stores result in Weaviate (write-through)
         └── Claude returns structured response
```
