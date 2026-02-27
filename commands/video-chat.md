---
description: Multi-turn video Q&A session
argument-hint: <youtube-url-or-file-path>
allowed-tools: mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_close, mcp__playwright__browser_wait_for, Write, Read, Edit, Glob, Bash
model: sonnet
---

# Video Chat: $ARGUMENTS

Start an interactive Q&A session with a video, progressively building knowledge.

## Session Setup

1. Determine the input type from "$ARGUMENTS":
   - If it starts with `http://` or `https://`: use `video_create_session` with `url` parameter
   - Otherwise (file path): use `video_create_session` with `file_path` parameter
2. Use description="Interactive Q&A session" for the session creation
3. Present the video title and session info

## Initialize Memory

1. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
2. Generate a slug from the video title: lowercase, hyphens, no special chars, max 50 chars
3. Check if a prior analysis exists at `<memory-dir>/gr/video/<slug>/analysis.md`
   - If yes: read it, note existing concepts and knowledge states. The chat builds on prior analysis.
   - If no: this chat creates a fresh knowledge entry.

4. Use `Write` to create `<memory-dir>/gr/video-chat/<slug>/analysis.md`:

```markdown
---
source: <youtube-url-or-file-path>
analyzed: <ISO 8601 timestamp>
updated: <ISO 8601 timestamp>
session_id: <session_id>
concepts: []
---

# <Video Title> — Chat Session

> Source: <url-or-path>
> Session started: <YYYY-MM-DD HH:MM>

## Q&A
```

5. Tell the user: **Session notes auto-saving to `gr/video-chat/<slug>/`**
6. Invite the user to ask questions about the video.

## Conversation Loop

For each follow-up question:

1. Use `video_continue_session` with the session_id and the user's prompt
2. Present the answer conversationally, citing timestamps when available
3. **Append to analysis.md** using `Edit` — add a timestamped Q&A entry:

```markdown

### Q: <user's question>  <!-- <YYYY-MM-DD HH:MM> -->

<Summarized answer with key timestamps>
```

4. **Track new concepts**: If the answer introduces new concepts not already in the YAML frontmatter:
   - Add them to the `concepts` array with `state: unknown`
   - Update the `updated` timestamp

5. After every 3-5 Q&A exchanges, briefly note if new concepts have accumulated that would enrich a visualization update. Don't generate the viz mid-conversation — just track.

## Session End

When the user is done (says "done", "thanks", changes topic, or explicitly ends):

### 1. Concept Extraction

Review all Q&A entries and extract:
- All concepts discussed (with timestamps where available)
- Relationships between concepts discovered during Q&A
- Any concepts the user seemed unclear on (mark as `fuzzy`) vs. ones they grasped (mark as `know`)

Update the YAML frontmatter with the complete concepts list and knowledge states.

### 2. Append Relationship Map

Add a summary section to analysis.md:

```markdown
## Session Summary  <!-- <YYYY-MM-DD HH:MM> -->

### Concepts Explored
- **<Concept 1>** — <brief description from Q&A context>
- **<Concept 2>** — <brief description>

### Relationships Discovered
- <Concept 1> → *clarified by* → <Concept 2>

### Knowledge Gaps
- <Concept X> — user seemed unsure about this (state: fuzzy)
```

### 3. Generate Visualization

1. Read `skills/gemini-visualize/SKILL.md` and `skills/gemini-visualize/templates/video-concept-map.md`
2. Generate `concept-map.html` from the accumulated concepts and relationships
3. Save to `<memory-dir>/gr/video-chat/<slug>/concept-map.html`

### 4. Screenshot Capture

1. Start HTTP server: `python3 -m http.server 18923 --directory <memory-dir>/gr/video-chat/<slug>/ &`
2. Navigate: `mcp__playwright__browser_navigate` → `http://localhost:18923/concept-map.html`
3. Wait: `mcp__playwright__browser_wait_for` (2 seconds for render)
4. Screenshot: `mcp__playwright__browser_take_screenshot` → save to `screenshot.png`
5. Cleanup: kill server, `mcp__playwright__browser_close`

If Playwright fails, skip gracefully — the HTML is the primary artifact.

### 5. Finalize

Append to analysis.md:

```markdown
## Visualization  <!-- <YYYY-MM-DD HH:MM> -->

![Concept Map](screenshot.png)
Interactive: [Open concept map](concept-map.html)
```

Confirm: **Session complete — saved to `gr/video-chat/<slug>/`**
- `analysis.md` — timestamped Q&A with concept tracking
- `concept-map.html` — interactive concept map
- `screenshot.png` — static capture

Suggest: browse past sessions with `/gr:recall video-chat`

## Cross-Referencing

If a prior `/gr:video` analysis exists for the same video (check `<memory-dir>/gr/video/<slug>/`):
- Note this in the session summary: "See also: full video analysis at `gr/video/<slug>/`"
- Consider concepts from the prior analysis when building the concept map — merge, don't duplicate
