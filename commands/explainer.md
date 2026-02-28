---
description: Full explainer video workflow — setup, inject content, generate pipeline, review, render
argument-hint: "<project-id> [step]"
allowed-tools: mcp__video-explainer__explainer_create, mcp__video-explainer__explainer_inject, mcp__video-explainer__explainer_status, mcp__video-explainer__explainer_list, mcp__video-explainer__explainer_generate, mcp__video-explainer__explainer_step, mcp__video-explainer__explainer_render, mcp__video-explainer__explainer_render_start, mcp__video-explainer__explainer_render_poll, mcp__video-explainer__explainer_short, mcp__video-explainer__explainer_refine, mcp__video-explainer__explainer_feedback, mcp__video-explainer__explainer_factcheck, mcp__video-explainer__explainer_sound, mcp__video-explainer__explainer_music, Read, Write, Glob
model: sonnet
---

# Explainer Video: $ARGUMENTS

Create and produce an explainer video from content.

## Workflow

### Phase 1: Setup

If `$ARGUMENTS` is a project ID that doesn't exist yet:
1. Call `explainer_create(project_id="$ARGUMENTS")`
2. Ask the user for content to inject, or look for files in the current directory

If the project exists, call `explainer_status` to see current progress.

### Phase 2: Content Injection

If the project's `input/` is empty:
1. Ask the user for content (research output, markdown, text)
2. Call `explainer_inject(project_id, content, filename)` to write it

### Phase 3: Pipeline Generation

Run the pipeline step by step, checking status between steps:

1. `explainer_step(project_id, "script")` — Generate the video script
2. Show the user the script and ask for feedback
3. If feedback: `explainer_feedback(project_id, feedback)` then `explainer_refine(project_id, "script")`
4. `explainer_step(project_id, "narration")` — Generate narration
5. `explainer_step(project_id, "scenes")` — Generate scene descriptions
6. `explainer_step(project_id, "voiceover")` — Generate voiceover audio
7. `explainer_step(project_id, "storyboard")` — Generate storyboard

Between each step, call `explainer_status` and report progress.

### Phase 4: Review

1. Call `explainer_factcheck(project_id)` to verify claims
2. Present results to the user
3. If issues found, use `explainer_refine` on affected phases

### Phase 5: Render

1. For preview: `explainer_render(project_id, resolution="720p", fast=True)`
2. For final: `explainer_render_start(project_id, resolution="1080p", fast=False)`
3. Poll with `explainer_render_poll(job_id)` every 30 seconds

### Phase 6: Extras (optional)

If the user wants:
- Sound effects: `explainer_sound(project_id, "analyze")` then `explainer_sound(project_id, "generate")`
- Background music: `explainer_music(project_id)`
- Short version: `explainer_short(project_id)`

## Output

After each phase, report:
- Current step completion status
- Any issues or warnings
- Next recommended action

## TTS Provider Notes

- **mock** (default): No audio — fastest for testing pipeline
- **elevenlabs**: Best quality, native timestamps (recommended for production)
- **openai**: Budget alternative, good quality
- **gemini**: Experimental option
- **edge**: Deprecated — unreliable due to auth breakage
