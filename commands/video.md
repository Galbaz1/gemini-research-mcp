---
name: video
description: Analyze a YouTube video with comprehensive extraction
argument-hint: <youtube-url>
allowed-tools: mcp__plugin_gemini-research_gemini-research__video_analyze, mcp__plugin_gemini-research_gemini-research__video_create_session, mcp__plugin_gemini-research_gemini-research__video_continue_session
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
