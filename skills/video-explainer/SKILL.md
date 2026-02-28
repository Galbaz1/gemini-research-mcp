---
name: video-explainer
description: Teaches Claude how to use the 15 video explainer tools to create explainer videos from research content. Activates when working with video synthesis, explainer creation, or the video-explainer MCP server.
---

# Video Explainer MCP — Tool Usage Guide

You have access to the `video-explainer-mcp` MCP server, which wraps the [video_explainer](https://github.com/prajwal-y/video_explainer) CLI to synthesize explainer videos from text content.

## Core Concept

This server is a **synthesis** companion to `video-research-mcp`. Research extracts knowledge; this server turns it into video. The pipeline is: content → script → narration → scenes → voiceover → storyboard → render.

## Tool Selection Guide

| I want to... | Use this tool |
|---|---|
| Create a new video project | `explainer_create` |
| Feed content into a project | `explainer_inject` |
| Check project progress | `explainer_status` |
| List all projects | `explainer_list` |
| Run the full pipeline | `explainer_generate` |
| Run one pipeline step | `explainer_step` |
| Preview render (blocking) | `explainer_render` |
| Start background render | `explainer_render_start` |
| Check render progress | `explainer_render_poll` |
| Generate short-form video | `explainer_short` |
| Improve a step's output | `explainer_refine` |
| Add iterative feedback | `explainer_feedback` |
| Verify script accuracy | `explainer_factcheck` |
| Add sound effects | `explainer_sound` |
| Add background music | `explainer_music` |

## Pipeline Order

Steps must run in order. Each step depends on the previous step's output:

```
1. script      — Generate video script from input content
2. narration   — Convert script to narration text
3. scenes      — Generate scene descriptions
4. voiceover   — Synthesize speech audio (TTS)
5. storyboard  — Create visual storyboard
6. render      — Combine into final video
```

Use `explainer_generate` to run all steps, or `explainer_step` for one at a time.

## Content Injection

Before running the pipeline, inject content:

```
explainer_create(project_id="quantum-computing")
explainer_inject(
    project_id="quantum-computing",
    content="# Quantum Computing\n\nKey concepts:\n- Superposition...",
    filename="research.md"
)
```

Content can be:
- Research output from `research_deep`
- Video analysis from `video_analyze`
- Any markdown or plain text

## Background Render Pattern

For long renders (1080p, 4K), use the start/poll pattern:

```
# Start render in background
result = explainer_render_start(project_id="my-video", resolution="1080p", fast=False)
job_id = result["job_id"]

# Poll every 30 seconds
status = explainer_render_poll(job_id=job_id)
# status["status"] is "pending", "running", "completed", or "failed"
```

## Quality Iteration Loop

After generating the pipeline:

1. `explainer_factcheck(project_id)` — Verify claims
2. `explainer_feedback(project_id, "Make the intro more engaging")` — Add notes
3. `explainer_refine(project_id, phase="script")` — Improve specific phase
4. Re-run dependent steps: `explainer_generate(project_id, from_step="narration")`

## TTS Provider Selection

| Provider | Quality | Cost | Timestamps | Status |
|----------|---------|------|------------|--------|
| `mock` | None | Free | N/A | **Default** — for testing |
| `elevenlabs` | Excellent | $165-330/1M chars | Native | **Recommended** |
| `openai` | Good | $15/1M chars | Whisper | Budget alternative |
| `gemini` | Good | ~$16/1M chars | Whisper | Experimental |
| `edge` | Variable | Free | Native | **Deprecated** — auth issues |

Set via `EXPLAINER_TTS_PROVIDER` in `~/.config/video-research-mcp/.env`.

## Error Handling

All tools return error dicts on failure:
```json
{
  "error": "description",
  "category": "SUBPROCESS_FAILED",
  "hint": "actionable fix",
  "retryable": false
}
```

Common categories:
- `EXPLAINER_NOT_FOUND` — Set `EXPLAINER_PATH`
- `PROJECT_NOT_FOUND` — Check project ID with `explainer_list`
- `NODE_NOT_FOUND` — Install Node.js 20+
- `FFMPEG_NOT_FOUND` — Install FFmpeg
- `TTS_FAILED` — Check TTS provider and API key
- `RENDER_FAILED` — Check Remotion installation
