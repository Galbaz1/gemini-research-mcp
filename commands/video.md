---
description: Analyze a YouTube video with comprehensive extraction
argument-hint: <youtube-url>
allowed-tools: mcp__gemini-research__video_analyze, mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, mcp__plugin_serena_serena__write_memory, mcp__plugin_serena_serena__list_memories
model: sonnet
---

# Video Analysis: $ARGUMENTS

Analyze the provided YouTube video URL.

## Steps

1. Use `video_analyze` with url="$ARGUMENTS" and instruction="Provide a comprehensive analysis including title, summary, key points, timestamps of important moments, main topics, and overall sentiment."
2. Present the structured results clearly:
   - **Title and Overview**
   - **Key Points** (bulleted)
   - **Timestamps** (notable moments)
   - **Topics and Sentiment**
3. Ask if the user wants to dive deeper into specific aspects:
   - Commands/tools shown: `instruction="Extract every CLI command with flags and arguments"`
   - Workflow/steps: `instruction="Extract the step-by-step workflow with timestamps"`
   - Transcript: `instruction="Transcribe with timestamps for each speaker change"`
4. For iterative Q&A, create a session with `video_create_session` and use `video_continue_session` for follow-ups

## Save to Memory

After presenting results, check if `write_memory` is in your available tools.

### If `write_memory` IS available:

1. Generate a slug from the video title: lowercase, hyphens, max 50 chars (e.g., "Mastering Claude Code Skills" → `mastering-claude-code-skills`)
2. Use `write_memory` with memory_name=`gr/video/<slug>` and content:

```markdown
# <Video Title>

> Analyzed on <today's date>
> Source: <youtube-url>

## Summary

<Overview paragraph>

## Key Points

<Bulleted key points>

## Timestamps

| Time | Moment |
|------|--------|
| ... | ... |

## Topics

<Comma-separated topics>
```

3. Confirm: **Saved to `gr/video/<slug>`** — browse past video notes with `/gr:recall video`

### If `write_memory` is NOT available:

Show this tip once, after the results:

> **Tip:** Want to save video notes across sessions? Install the Serena plugin:
> ```
> claude plugin install serena@claude-plugins-official
> ```
> Then restart Claude Code. Your future `/gr:video` results will be auto-saved and browsable via `/gr:recall`.
