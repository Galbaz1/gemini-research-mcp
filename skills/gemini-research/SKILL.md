---
name: gemini-research
description: Teaches Claude how to effectively use the 11 Gemini research tools. Activates when working with video analysis, deep research, content extraction, or web search via the gemini-research MCP server.
---

# Gemini Research MCP — Tool Usage Guide

You have access to the `gemini-research-mcp` MCP server, which exposes 11 tools powered by Gemini 3.1 Pro. These tools are **instruction-driven** — you write the instruction, Gemini returns structured JSON.

## Core Principle

Tools accept an `instruction` parameter instead of fixed modes. Write specific, actionable instructions. The more precise your instruction, the better the structured output.

## Tool Selection Guide

| I want to... | Use this tool |
|---|---|
| Analyze a YouTube video | `video_analyze` |
| Have a multi-turn conversation about a video | `video_create_session` + `video_continue_session` |
| Research a topic in depth | `research_deep` |
| Plan a research strategy | `research_plan` |
| Verify a specific claim | `research_assess_evidence` |
| Analyze a URL, file, or text | `content_analyze` |
| Extract structured data from content | `content_extract` |
| Search the web for current info | `web_search` |
| Check or clear the cache | `infra_cache` |
| Change model/thinking/temperature | `infra_configure` |

## Tool Reference

### Video Tools (3)

#### `video_analyze` — Analyze any YouTube video
```
video_analyze(
  url: str,                    # YouTube URL (required)
  instruction: str = "...",     # What to analyze (default: comprehensive analysis)
  output_schema: dict | None,   # Custom JSON Schema for response shape
  thinking_level: str = "high", # minimal | low | medium | high
  use_cache: bool = True        # Cache results by instruction hash
)
```

**Default output** (VideoResult): `{title, summary, key_points[], timestamps[{time, description}], topics[], sentiment, url}`

**Writing good instructions:**
- BAD: "analyze this video" (too vague, just use the default)
- GOOD: "Extract every CLI command demonstrated, including flags and arguments"
- GOOD: "List all recipes shown with ingredients and cooking times"
- GOOD: "Transcribe this video with timestamps for each speaker change"
- GOOD: "Identify the 3 most controversial claims and rate their evidence strength"

**When to use custom output_schema:**
Use when the default VideoResult shape doesn't match what you need:
```json
{
  "type": "object",
  "properties": {
    "recipes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "ingredients": {"type": "array", "items": {"type": "string"}},
          "steps": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

**Common instruction patterns:**
- Transcript: `instruction="Transcribe with timestamps"`
- Tutorial extraction: `instruction="Extract commands, tools, and step-by-step workflow"`
- Comparison prep: Call `video_analyze` on each URL with the same instruction, then synthesize

#### `video_create_session` — Start multi-turn video exploration
```
video_create_session(url: str, description: str = "")
```
Returns `{session_id, status, video_title}`. Use for iterative Q&A about one video.

#### `video_continue_session` — Follow up within a session
```
video_continue_session(session_id: str, prompt: str)
```
Returns `{response, turn_count}`. Maintains conversation history across turns.

### Content Tools (2)

#### `content_analyze` — Analyze any content (file, URL, or text)
```
content_analyze(
  instruction: str = "...",     # What to analyze
  file_path: str | None,        # Local file (PDF or text)
  url: str | None,              # URL to fetch and analyze
  text: str | None,             # Raw text
  output_schema: dict | None,   # Custom JSON Schema
  thinking_level: str = "medium"
)
```

**Provide exactly one of** `file_path`, `url`, or `text`.

**Default output** (ContentResult): `{title, summary, key_points[], entities[], structure_notes, quality_assessment}`

**Examples:**
- Summarize a webpage: `content_analyze(url="https://...", instruction="Summarize in 3 sentences")`
- Extract from PDF: `content_analyze(file_path="paper.pdf", instruction="Extract methodology with statistical methods")`
- Analyze text: `content_analyze(text="...", instruction="List all named entities with types")`

#### `content_extract` — Extract structured data with caller-provided schema
```
content_extract(content: str, schema: dict)
```
Use when you have a specific JSON Schema and want guaranteed structured extraction.

### Research Tools (3)

#### `research_deep` — Multi-phase deep research
```
research_deep(
  topic: str,                    # Research question (3-500 chars)
  scope: str = "moderate",       # quick | moderate | deep | comprehensive
  thinking_level: str = "high"
)
```
Runs 3 phases: Scope Definition > Evidence Collection > Synthesis.
Returns `{topic, scope, executive_summary, findings[{claim, evidence_tier, supporting[], contradicting[], reasoning}], open_questions[], methodology_critique}`.

Evidence tiers: CONFIRMED, STRONG INDICATOR, INFERENCE, SPECULATION, UNKNOWN.

#### `research_plan` — Generate research orchestration blueprint
```
research_plan(topic: str, scope: str = "moderate", available_agents: int = 10)
```
Returns a phased blueprint with task decomposition and model assignments. Does NOT execute — provides the plan.

#### `research_assess_evidence` — Assess a claim against sources
```
research_assess_evidence(claim: str, sources: list[str], context: str = "")
```
Returns `{claim, tier, confidence, supporting[], contradicting[], reasoning}`.

### Search Tool (1)

#### `web_search` — Google Search via Gemini grounding
```
web_search(query: str, num_results: int = 5)
```
Returns `{query, response, sources[{title, url}]}`. Uses Gemini Flash with Google Search.

### Infrastructure Tools (2)

#### `infra_cache` — Manage analysis cache
```
infra_cache(action="stats" | "list" | "clear", content_id=None)
```

#### `infra_configure` — Runtime config changes
```
infra_configure(model=None, thinking_level=None, temperature=None)
```

## Workflow Patterns

### Research a topic end-to-end
1. `research_plan(topic)` > orchestration blueprint
2. `web_search(query)` > gather current sources
3. `research_deep(topic, scope="deep")` > full analysis with evidence tiers
4. `research_assess_evidence(claim, sources)` > verify specific claims

### Analyze a video for a specific use case
1. `video_analyze(url, instruction="Provide a comprehensive analysis")` > overview
2. `video_analyze(url, instruction="Extract all code examples with context")` > deep dive
3. Or use sessions for iterative exploration:
   - `video_create_session(url)` > get session_id
   - `video_continue_session(session_id, "What libraries are used?")` > follow up

### Compare multiple videos (orchestrated by you)
1. Call `video_analyze` on each URL with the same instruction
2. Synthesize the results in your response — you are the comparison engine

### Extract structured data from documents
1. `content_analyze(file_path="paper.pdf", instruction="Summarize methodology")` > overview
2. `content_extract(content=text, schema={...})` > precise structured extraction

## Error Handling

All tools return error dicts instead of raising:
```json
{"error": "message", "category": "API_QUOTA_EXCEEDED", "hint": "wait a minute", "retryable": true}
```
Always check for `"error"` key in the response before processing results. If `retryable` is true, wait and retry.

## Caching

Results are cached by `{content_id}_{tool}_{instruction_hash}_{model_hash}`. Different instructions for the same content produce separate cache entries. Use `use_cache=False` to force fresh analysis.

## Thinking Levels

| Level | When to use |
|-------|-------------|
| `minimal` | Simple extraction (title, basic facts) |
| `low` | Quick summaries, simple tasks |
| `medium` | Content analysis (default for content tools) |
| `high` | Video analysis, research, complex reasoning (default for video/research) |
