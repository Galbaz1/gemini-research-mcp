---
description: Analyze any content — URL, file, or pasted text
argument-hint: <url|file-path|text>
allowed-tools: mcp__video-research__content_analyze, mcp__video-research__content_extract, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_close, mcp__playwright__browser_wait_for, Write, Glob, Read, Bash
model: sonnet
---

# Content Analysis: $ARGUMENTS

Analyze the provided content with progressive memory saving and automatic knowledge-graph visualization.

## Phase 1: Analyze

1. Determine the input type from "$ARGUMENTS":
   - If it starts with `http://` or `https://`: use `content_analyze` with `url` parameter
   - If it looks like a file path (contains `/` or `.`extension): use `content_analyze` with `file_path` parameter
   - Otherwise: use `content_analyze` with `text` parameter
2. Use instruction="Provide a comprehensive analysis including title, summary, key points, important entities (people, organizations, concepts, technologies), document structure, and quality assessment."

## Phase 2: Present & Save Initial Results

1. Present results clearly:
   - **Title and Source**
   - **Summary** (2-3 sentences)
   - **Key Points** (bulleted)
   - **Entities** (people, organizations, concepts)
   - **Quality Assessment**

2. **Immediately save initial results**:
   a. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
   b. Generate a slug from the content title or source: lowercase, hyphens, no special chars, max 50 chars (e.g., "Attention Is All You Need" → `attention-is-all-you-need`, a URL like `arxiv.org/abs/2401.12345` → `arxiv-2401-12345`)
   c. Use `Write` to save at `<memory-dir>/gr/analysis/<slug>/analysis.md`:

```markdown
---
source: <url, file path, or "pasted text">
analyzed: <ISO 8601 timestamp>
updated: <ISO 8601 timestamp>
entities:
  people: <count>
  organizations: <count>
  concepts: <count>
  technologies: <count>
---

# <Title>

> Source: <url, file path, or "pasted text">
> Analyzed on <YYYY-MM-DD HH:MM>

## Summary  <!-- <YYYY-MM-DD HH:MM> -->

<2-3 sentence summary>

## Key Points  <!-- <YYYY-MM-DD HH:MM> -->

<Bulleted key points>

## Entities  <!-- <YYYY-MM-DD HH:MM> -->

### People
- <Person 1> — <role/context>

### Organizations
- <Org 1> — <context>

### Concepts
- <Concept 1> — <brief definition>

### Technologies
- <Tech 1> — <context>

## Quality Assessment  <!-- <YYYY-MM-DD HH:MM> -->

<Assessment of content quality, reliability, completeness>
```

   d. Tell the user: **Saved initial analysis to `gr/analysis/<slug>/`**

## Phase 3: Enrich with Knowledge Graph

1. Map the content analysis into a knowledge graph structure:
   - The content itself is the central anchor node
   - Each entity becomes a node (typed by category)
   - Key points become larger rectangular nodes
   - Relationships between entities are inferred from the content

2. Append a Knowledge Graph section to `analysis.md`:

```markdown
## Knowledge Graph  <!-- <YYYY-MM-DD HH:MM> -->

### Entities
- **<Entity 1>** (Person) — <description>
- **<Entity 2>** (Concept) — <description>

### Relationships
- <Entity 1> → *authored* → <Entity 3>
- <Entity 2> → *implements* → <Entity 4>
- <Key Point 1> → *mentions* → <Entity 1>
```

3. Update the `updated` timestamp in frontmatter.

## Phase 4: Generate Visualization

1. Read `skills/gemini-visualize/SKILL.md`
2. Read `skills/gemini-visualize/templates/content-knowledge-graph.md`
3. Generate a **single self-contained HTML file** (`knowledge-graph.html`) following the template:
   - Map entities to nodes colored by type (Person=teal, Org=blue, Concept=purple, Tech=green)
   - Map relationships to edges with labels
   - Key points as wider pill-shaped nodes
   - Central content anchor node
   - Entity type filter checkboxes
   - Radial layout from center
   - Prompt generation for extraction refinement
4. Use `Write` to save at `<memory-dir>/gr/analysis/<slug>/knowledge-graph.html`

**User override**: If the user said "skip visualization" or "no viz", skip Phases 4 and 5.

## Phase 5: Screenshot Capture

1. Start HTTP server:
   ```
   Bash: lsof -ti:18923 | xargs kill -9 2>/dev/null; python3 -m http.server 18923 --directory <memory-dir>/gr/analysis/<slug>/ &
   ```

2. Navigate: `mcp__playwright__browser_navigate` → `http://localhost:18923/knowledge-graph.html`

3. Wait: `mcp__playwright__browser_wait_for` (2 seconds for render)

4. Screenshot: `mcp__playwright__browser_take_screenshot` → save to `screenshot.png`

5. Cleanup: kill server, `mcp__playwright__browser_close`

If Playwright fails, skip gracefully.

## Phase 6: Finalize & Link

1. Append to `analysis.md`:

```markdown
## Visualization  <!-- <YYYY-MM-DD HH:MM> -->

![Knowledge Graph](screenshot.png)
Interactive: [Open knowledge graph](knowledge-graph.html)
```

2. Update the `updated` timestamp.

3. Confirm: **Analysis complete — saved to `gr/analysis/<slug>/`**
   - `analysis.md` — timestamped analysis with entity graph
   - `knowledge-graph.html` — interactive knowledge graph
   - `screenshot.png` — static capture

## Phase 7: Workspace Output

Copy all artifacts to the user's workspace. Use Python `shutil` (bash `cp` may be sandboxed):

```
Bash: python3 -c "
import shutil, os
src = '<memory-dir>/gr/analysis/<slug>'
dst = os.path.join(os.getcwd(), 'output', '<slug>')
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)
print(f'Copied to output/<slug>/')
"
```

Tell the user: **Output also saved to `output/<slug>/`** in your workspace.

If the workspace copy fails, it's non-critical — the memory copy is authoritative.

## Deeper Exploration

Offer to extract specific structured data with `content_extract` if the user needs a particular schema. Any deeper analysis appends timestamped sections to the existing `analysis.md` and may trigger a visualization update.
