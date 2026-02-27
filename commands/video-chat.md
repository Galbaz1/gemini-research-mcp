---
description: Multi-turn video Q&A session
argument-hint: <youtube-url>
allowed-tools: mcp__plugin_gr_gemini-research__video_create_session, mcp__plugin_gr_gemini-research__video_continue_session
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
