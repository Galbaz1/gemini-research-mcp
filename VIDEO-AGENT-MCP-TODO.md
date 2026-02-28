# video-agent-mcp — Remaining Work

Phase 1 (parallel scene generation) is complete and merged via PR #16.
This document tracks what remains from the original implementation plan.

---

## Phase 2 — Full Pipeline Tools

Replace the remaining sequential LLM steps in `video-explainer` with
parallel Agent SDK calls.

### New files

| File | Content |
|------|---------|
| `prompts/pipeline.py` | Analysis, script, and narration prompts ported from upstream |
| `tools/pipeline.py` | Three new tools (see below) |
| `tests/test_pipeline_tools.py` | ~9 tests, all mocked |

### New tools

| Tool | Replaces |
|------|---------|
| `agent_analyze_content(project_id)` | `explainer_step … analyze` |
| `agent_generate_script(project_id, duration_seconds)` | `explainer_step … script` |
| `agent_generate_narrations(project_id)` | `explainer_step … narration` |

### Updated pipeline flow (after Phase 2)

```
1. explainer_create(project_id)
2. explainer_inject(project_id, content)
3. agent_analyze_content(project_id)          ← agent MCP
4. agent_generate_script(project_id, 90)      ← agent MCP
5. agent_generate_narrations(project_id)      ← agent MCP
6. explainer_step(project_id, "voiceover")
7. agent_generate_scenes(project_id, concurrency=5)  ← agent MCP (Phase 1)
8. explainer_step(project_id, "storyboard")
9. explainer_render(project_id)
```

### Existing files to update

| File | Change |
|------|--------|
| `bin/lib/config.js` | Add `video-agent` to `MCP_SERVERS` map |
| `skills/video-explainer/SKILL.md` | Add "Agent-Accelerated Tools" section with tool table + when-to-use guide |
| `commands/explainer.md` | Phase 3 steps: replace `explainer_step` with `agent_*` for LLM steps |
| `commands/explain-video.md` | Same update |

---

## Phase 3 — TSX Validation + Retry

Add lightweight validation and automatic per-scene retry to reduce
failure rate without blocking the parallel execution pipeline.

### New files

| File | Content |
|------|---------|
| `validation.py` (~100 lines) | Bracket/tag balancing, JSX export detection, basic syntax checks |

### Changes to existing files

| File | Change |
|------|--------|
| `tools/scenes.py` | Wrap `_process_scene_result` with validate → regenerate-with-feedback loop (max 3 attempts per scene, within the same parallel task) |

### Validation checks

- Balanced `{` / `}` braces
- Balanced JSX tags (heuristic — no full parse)
- `export const <ComponentName>` present in output
- No placeholder comments like `// TODO` or `{/* placeholder */}`

---

## Phase 4 — Direct Anthropic API (Future)

Replace `claude-agent-sdk.query()` with `anthropic.AsyncAnthropic` calls.

**Why:** Eliminates ~3 s subprocess overhead per scene query.
**Risk:** Agent SDK handles auth/retry automatically; direct API requires manual handling.
**Prerequisite:** Confirm subprocess overhead is measurable on production hardware.

### Changes

| File | Change |
|------|--------|
| `sdk_runner.py` | Swap `claude_agent_sdk.query()` for `anthropic.AsyncAnthropic().messages.create()` |
| `pyproject.toml` | Add `anthropic>=0.40` dependency |
| `config.py` | Add `ANTHROPIC_API_KEY` validation |

`run_parallel_queries()` interface stays identical — no tool changes required.

---

## Plugin Installer Registration

Once Phase 2 tools are stable, register the `video-agent-mcp` server in the
npm plugin installer so users get it automatically with `npx video-research-mcp@latest`.

| File | Change |
|------|--------|
| `bin/lib/config.js` | Add `video-agent-mcp` entry to `MCP_SERVERS` |
| `bin/lib/copy.js` | Add any new commands/skills to `FILE_MAP` |

---

## Open Questions

- **`claude-agent-sdk` stability** — currently `>=0.1.0`; watch for breaking changes
  and migrate to stable `claude-sdk` when published
- **Rate limit tuning** — default `AGENT_CONCURRENCY=5` chosen conservatively;
  validate against actual Anthropic API rate limits for the chosen model tier
- **Prompt drift** — prompts are extracted snapshots from `video_explainer`;
  establish a process to sync when the upstream generator changes
