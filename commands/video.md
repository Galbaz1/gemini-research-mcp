---
description: Analyze a video (YouTube URL, local file, or directory)
argument-hint: <youtube-url-or-file-path>
allowed-tools: mcp__gemini-research__video_analyze, mcp__gemini-research__video_batch_analyze, mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_close, mcp__playwright__browser_wait_for, Write, Glob, Read, Bash
model: sonnet
---

# Video Analysis: $ARGUMENTS

Analyze the provided video source with progressive memory saving and automatic visualization.

## Phase 1: Analyze

1. Determine the input type from "$ARGUMENTS":
   - If it starts with `http://` or `https://`: use `video_analyze` with `url` parameter
   - If it's a directory path (ends with `/` or is a known directory): use `video_batch_analyze` with `directory` parameter
   - Otherwise (file path): use `video_analyze` with `file_path` parameter
2. For single video analysis, use instruction="Provide a comprehensive analysis including title, summary, key points, timestamps of important moments, main topics, and overall sentiment."
3. For batch (directory) analysis, use instruction="Provide a comprehensive analysis of this video."

## Phase 2: Present & Save Initial Results

1. Present the structured results clearly:
   - **Title and Overview**
   - **Key Points** (bulleted)
   - **Timestamps** (notable moments)
   - **Topics and Sentiment**

2. **Immediately save initial results** — don't wait until the end:
   a. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
   b. Generate a slug from the video title: lowercase, hyphens, no special chars, max 50 chars (e.g., "Mastering Claude Code Skills" → `mastering-claude-code-skills`)
   c. Use `Write` to save at `<memory-dir>/gr/video/<slug>/analysis.md`:

```markdown
---
source: <youtube-url-or-file-path>
analyzed: <ISO 8601 timestamp>
updated: <ISO 8601 timestamp>
concepts: []
---

# <Video Title>

> Source: <url-or-path>
> First analyzed: <YYYY-MM-DD HH:MM>

## Summary  <!-- <YYYY-MM-DD HH:MM> -->

<Overview paragraph>

## Key Points  <!-- <YYYY-MM-DD HH:MM> -->

<Bulleted key points>

## Timestamps  <!-- <YYYY-MM-DD HH:MM> -->

| Time | Moment |
|------|--------|
| ... | ... |

## Topics  <!-- <YYYY-MM-DD HH:MM> -->

<Comma-separated topics>
```

   d. Tell the user: **Saved initial analysis to `gr/video/<slug>/`**

## Phase 3: Enrich with Relationships

1. Extract concepts, relationships, and categories from the analysis results:
   - Identify 8-20 key concepts from key_points, topics, and timestamps
   - Infer relationships between concepts (builds on, example of, enables, contradicts, related to)
   - Cluster concepts into 3-7 categories by topic
   - Assign initial knowledge states: all `unknown`

2. Append a Relationship Map section to `analysis.md` using `Write` (re-read and rewrite):

```markdown
## Relationship Map  <!-- <YYYY-MM-DD HH:MM> -->

### Concepts
- **<Concept 1>** (<category>) — <one-line description>. Timestamp: <time>
- **<Concept 2>** (<category>) — <one-line description>. Timestamp: <time>

### Relationships
- <Concept 1> → *enables* → <Concept 2>
- <Concept 3> → *example of* → <Concept 1>
```

3. Update the YAML frontmatter `concepts` array:

```yaml
concepts:
  - name: <Concept 1>
    state: unknown
    timestamp: "<time>"
  - name: <Concept 2>
    state: unknown
    timestamp: "<time>"
```

4. Update the `updated` timestamp in frontmatter.

## Phase 4: Generate Visualization

1. Read the visualization skill: `skills/gemini-visualize/SKILL.md`
2. Read the video template: `skills/gemini-visualize/templates/video-concept-map.md`
3. Generate a **single self-contained HTML file** (`concept-map.html`) following the template:
   - Map extracted concepts to nodes with categories and colors
   - Map relationships to edges with labels
   - Include knowledge state cycling (Know/Fuzzy/Unknown)
   - Include prompt generation button
   - Dark theme, canvas rendering, drag-and-drop, zoom/pan
4. Use `Write` to save at `<memory-dir>/gr/video/<slug>/concept-map.html`

**User override**: If the user said "skip visualization" or "no viz", skip Phases 4 and 5 entirely.

## Phase 5: Screenshot Capture

1. Start a background HTTP server:
   ```
   Bash: python3 -m http.server 18923 --directory <memory-dir>/gr/video/<slug>/ &
   ```
   Capture the PID from output.

2. Navigate Playwright to the visualization:
   ```
   mcp__playwright__browser_navigate → http://localhost:18923/concept-map.html
   ```

3. Wait for rendering:
   ```
   mcp__playwright__browser_wait_for → selector: "canvas" or wait 2 seconds
   ```

4. Take screenshot:
   ```
   mcp__playwright__browser_take_screenshot
   ```
   Save the screenshot data to `<memory-dir>/gr/video/<slug>/screenshot.png`

5. Cleanup:
   ```
   Bash: kill <PID>
   mcp__playwright__browser_close
   ```

6. If any Playwright step fails, log the error but continue — the HTML is the primary artifact.

## Phase 6: Finalize & Link

1. Update `analysis.md` to add the Visualization section at the end:

```markdown
## Visualization  <!-- <YYYY-MM-DD HH:MM> -->

![Concept Map](screenshot.png)
Interactive: [Open concept map](concept-map.html)
```

2. Update the `updated` timestamp in YAML frontmatter.

3. Confirm: **Analysis complete — saved to `gr/video/<slug>/`**
   - `analysis.md` — timestamped analysis with relationship map
   - `concept-map.html` — interactive concept map
   - `screenshot.png` — static capture

## Deeper Exploration

After presenting results, ask if the user wants to dive deeper:
- Commands/tools shown: `instruction="Extract every CLI command with flags and arguments"`
- Workflow/steps: `instruction="Extract the step-by-step workflow with timestamps"`
- Transcript: `instruction="Transcribe with timestamps for each speaker change"`
- Start a chat session: suggest `/gr:video-chat <same-url>`

For iterative Q&A, create a session with `video_create_session` and use `video_continue_session` for follow-ups. Any deeper analysis should be appended to the existing `analysis.md` with new timestamps.
