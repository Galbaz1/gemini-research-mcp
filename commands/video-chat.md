---
description: Multi-turn video Q&A session
argument-hint: <youtube-url>
allowed-tools: mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, Write, Read, Edit, Glob
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

This command uses a running notes approach — building up the memory as the conversation progresses.

1. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
2. Generate a slug from the video title: lowercase, hyphens, no special chars, max 50 chars

**After creating the session (step 2):**

Use `Write` to create `<memory-dir>/gr/video-chat/<slug>.md`:

```markdown
# <Video Title>

> Session started on <today's date>
> Source: <youtube-url>

## Q&A
```

Tell the user: **Session notes will auto-save to `gr/video-chat/<slug>`**

**After each follow-up answer (step 4-5):**

Use `Edit` to append to the file:

```markdown

### Q: <user's question>

<summarized answer with key timestamps>
```

**When the user is done or changes topic:**

Confirm: **Session notes saved to `gr/video-chat/<slug>`** — review anytime with `/gr:recall video-chat`
