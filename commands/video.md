---
description: Analyze a YouTube video with comprehensive extraction
argument-hint: <youtube-url>
allowed-tools: mcp__gemini-research__video_analyze, mcp__gemini-research__video_create_session, mcp__gemini-research__video_continue_session, Write, Glob, Read
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

After presenting results, auto-save to the project's memory directory for future reference.

1. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
2. Generate a slug from the video title: lowercase, hyphens, no special chars, max 50 chars (e.g., "Mastering Claude Code Skills" → `mastering-claude-code-skills`)
3. Use `Write` to save the file at `<memory-dir>/gr/video/<slug>.md`:

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

4. Confirm: **Saved to `gr/video/<slug>`** — browse past video notes with `/gr:recall video`
