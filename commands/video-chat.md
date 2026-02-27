---
description: Multi-turn video Q&A session
argument-hint: <youtube-url>
allowed-tools: mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, mcp__plugin_serena_serena__write_memory, mcp__plugin_serena_serena__read_memory, mcp__plugin_serena_serena__edit_memory, mcp__plugin_serena_serena__list_memories
model: sonnet
---

# Video Chat: $ARGUMENTS

Start an interactive Q&A session with a YouTube video.

## Steps

1. Use `video_create_session` with url="$ARGUMENTS" and description="Interactive Q&A session"
2. Present the video title and session info
3. Invite the user to ask questions about the video
4. For each follow-up question, use `video_continue_session` with the session_id and the user's prompt
5. Present answers conversationally, citing timestamps when available

## Save to Memory

This command uses a running notes approach — building up memory as the conversation progresses.
Check if `write_memory` is in your available tools.

### If `write_memory` IS available:

**After creating the session (step 2):**

1. Generate a slug from the video title: lowercase, hyphens, max 50 chars
2. Use `write_memory` with memory_name=`gr/video-chat/<slug>` and initial content:

```markdown
# <Video Title>

> Session started on <today's date>
> Source: <youtube-url>

## Q&A
```

3. Tell the user: **Session notes will auto-save to `gr/video-chat/<slug>`**

**After each follow-up answer (step 4-5):**

Use `edit_memory` with memory_name=`gr/video-chat/<slug>`, mode="regex", needle=`\z` (end of content), and append:

```markdown

### Q: <user's question>

<summarized answer with key timestamps>
```

**When the user is done or changes topic:**

Confirm: **Session notes saved to `gr/video-chat/<slug>`** — review anytime with `/gr:recall video-chat`

### If `write_memory` is NOT available:

Show this tip once, when creating the session:

> **Tip:** Want to save video Q&A sessions across sessions? Install the Serena plugin:
> ```
> claude plugin install serena@claude-plugins-official
> ```
> Then restart Claude Code. Your future `/gr:video-chat` sessions will be auto-saved and browsable via `/gr:recall`.
