---
description: Deep research on any topic with evidence-tier labeling
argument-hint: <topic>
allowed-tools: mcp__video-research__web_search, mcp__video-research__research_deep, mcp__video-research__research_plan, mcp__video-research__research_assess_evidence, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_close, mcp__playwright__browser_wait_for, Write, Glob, Read, Bash
model: sonnet
---

# Research: $ARGUMENTS

Run a multi-phase deep research analysis with progressive memory saving and automatic evidence-network visualization.

## Phase 1: Research

1. Use `web_search` to gather current sources on "$ARGUMENTS"
2. Use `research_deep` with topic="$ARGUMENTS", scope="moderate", thinking_level="high"

## Phase 2: Present & Save Initial Results

1. Present findings organized by evidence tier:
   - **CONFIRMED** — Multiple independent sources agree
   - **STRONG INDICATOR** — Credible evidence with minor gaps
   - **INFERENCE** — Reasonable conclusion from indirect evidence
   - **SPECULATION** — Plausible but unverified
   - **UNKNOWN** — Insufficient evidence
2. Highlight open questions and methodology critique

3. **Immediately save initial results**:
   a. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
   b. Generate a slug from the topic: lowercase, hyphens, no special chars, max 50 chars (e.g., "impact of mcp on ai agents" → `impact-of-mcp-on-ai-agents`)
   c. Use `Write` to save at `<memory-dir>/gr/research/<slug>/analysis.md`:

```markdown
---
source: web research
topic: "$ARGUMENTS"
analyzed: <ISO 8601 timestamp>
updated: <ISO 8601 timestamp>
scope: moderate
findings_count: <number>
evidence_tiers:
  confirmed: <count>
  strong_indicator: <count>
  inference: <count>
  speculation: <count>
  unknown: <count>
---

# $ARGUMENTS

> Researched on <YYYY-MM-DD HH:MM>
> Scope: moderate

## Executive Summary  <!-- <YYYY-MM-DD HH:MM> -->

<2-3 sentence summary>

## Findings  <!-- <YYYY-MM-DD HH:MM> -->

### CONFIRMED
1. **<Finding>** — <evidence summary>

### STRONG INDICATOR
2. **<Finding>** — <evidence summary>

### INFERENCE
3. **<Finding>** — <evidence summary>

### SPECULATION
4. **<Finding>** — <evidence summary>

### UNKNOWN
5. **<Finding>** — <evidence summary>

## Sources  <!-- <YYYY-MM-DD HH:MM> -->

<Cited sources with URLs where available>

## Open Questions  <!-- <YYYY-MM-DD HH:MM> -->

<Unresolved questions for future investigation>

## Methodology Critique  <!-- <YYYY-MM-DD HH:MM> -->

<Assessment of research methodology limitations>
```

   d. Tell the user: **Saved initial research to `gr/research/<slug>/`**

## Phase 3: Enrich with Evidence Network

1. Map the research findings into a network structure:
   - Each finding becomes a node with its evidence tier
   - Open questions become nodes (distinct style)
   - Supporting/contradicting relationships between findings become edges
   - Shared sources create implicit "related to" edges between findings

2. Append an Evidence Network section to `analysis.md`:

```markdown
## Evidence Network  <!-- <YYYY-MM-DD HH:MM> -->

### Nodes
- **Finding 1** (CONFIRMED) — <claim summary>
- **Finding 2** (INFERENCE) — <claim summary>
- **Open Question 1** — <question>

### Relationships
- Finding 1 → *supports* → Finding 3
- Finding 2 → *contradicts* → Finding 4
- Open Question 1 → *challenges* → Finding 2
```

3. Update the `updated` timestamp in frontmatter.

## Phase 4: Generate Visualization

1. Read `skills/gemini-visualize/SKILL.md`
2. Read `skills/gemini-visualize/templates/research-evidence-net.md`
3. Generate a **single self-contained HTML file** (`evidence-net.html`) following the template:
   - Map findings to nodes colored by evidence tier
   - Map relationships to edges (supports=green, contradicts=red, related=gray)
   - Open questions as purple dashed-border nodes
   - Evidence tier filter checkboxes
   - Hierarchical layout (CONFIRMED at top, UNKNOWN at bottom)
   - Prompt generation for follow-up research
4. Use `Write` to save at `<memory-dir>/gr/research/<slug>/evidence-net.html`

**User override**: If the user said "skip visualization" or "no viz", skip Phases 4 and 5.

## Phase 5: Screenshot Capture

1. Start HTTP server:
   ```
   Bash: lsof -ti:18923 | xargs kill -9 2>/dev/null; python3 -m http.server 18923 --directory <memory-dir>/gr/research/<slug>/ &
   ```

2. Navigate: `mcp__playwright__browser_navigate` → `http://localhost:18923/evidence-net.html`

3. Wait: `mcp__playwright__browser_wait_for` (2 seconds for render)

4. Screenshot: `mcp__playwright__browser_take_screenshot` → save to `screenshot.png`

5. Cleanup: kill server, `mcp__playwright__browser_close`

If Playwright fails, skip gracefully.

## Phase 6: Finalize & Link

1. Append to `analysis.md`:

```markdown
## Visualization  <!-- <YYYY-MM-DD HH:MM> -->

![Evidence Network](screenshot.png)
Interactive: [Open evidence network](evidence-net.html)
```

2. Update the `updated` timestamp.

3. Confirm: **Research complete — saved to `gr/research/<slug>/`**
   - `analysis.md` — timestamped findings with evidence tiers
   - `evidence-net.html` — interactive evidence network
   - `screenshot.png` — static capture

## Phase 7: Workspace Output

Copy all artifacts to the user's workspace. Use Python `shutil` (bash `cp` may be sandboxed):

```
Bash: python3 -c "
import shutil, os
src = '<memory-dir>/gr/research/<slug>'
dst = os.path.join(os.getcwd(), 'output', '<slug>')
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)
print(f'Copied to output/<slug>/')
"
```

Tell the user: **Output also saved to `output/<slug>/`** in your workspace.

If the workspace copy fails, it's non-critical — the memory copy is authoritative.

## Deeper Analysis

If the user wants deeper analysis, offer:
- Re-run with scope="deep" or "comprehensive" — results append to existing analysis.md with new timestamps
- Verify specific claims with `research_assess_evidence` — append verification results
- Broader context with `web_search` for specific sub-topics

Any deeper analysis appends timestamped sections to the existing `analysis.md` and may trigger a visualization update.
