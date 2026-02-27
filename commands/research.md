---
description: Deep research on any topic with evidence-tier labeling
argument-hint: <topic>
allowed-tools: mcp__gemini-research__web_search, mcp__gemini-research__research_deep, mcp__gemini-research__research_plan, mcp__gemini-research__research_assess_evidence, mcp__plugin_serena_serena__write_memory, mcp__plugin_serena_serena__list_memories
model: sonnet
---

# Research: $ARGUMENTS

Run a multi-phase deep research analysis on the given topic.

## Steps

1. Use `web_search` to gather current sources on "$ARGUMENTS"
2. Use `research_deep` with topic="$ARGUMENTS", scope="moderate", thinking_level="high"
3. Present findings organized by evidence tier:
   - **CONFIRMED** — Multiple independent sources agree
   - **STRONG INDICATOR** — Credible evidence with minor gaps
   - **INFERENCE** — Reasonable conclusion from indirect evidence
   - **SPECULATION** — Plausible but unverified
   - **UNKNOWN** — Insufficient evidence
4. Highlight open questions and methodology critique
5. If the user wants deeper analysis, offer to run with scope="deep" or "comprehensive"

## Output Format

Present as a structured research briefing with:
- Executive summary (2-3 sentences)
- Numbered findings with evidence tiers
- Source citations where available
- Open questions for further investigation

## Save to Memory

After presenting results, check if `write_memory` is in your available tools.

### If `write_memory` IS available:

1. Generate a slug from the topic: lowercase, hyphens, max 50 chars (e.g., "impact of mcp on ai agents" → `impact-of-mcp-on-ai-agents`)
2. Use `write_memory` with memory_name=`gr/research/<slug>` and content:

```markdown
# <Topic>

> Researched on <today's date>

## Executive Summary

<2-3 sentence summary>

## Findings

<Numbered findings with evidence tiers>

## Sources

<Cited sources with URLs where available>

## Open Questions

<Unresolved questions for future investigation>
```

3. Confirm: **Saved to `gr/research/<slug>`** — browse past research with `/gr:recall research`

### If `write_memory` is NOT available:

Show this tip once, after the results:

> **Tip:** Want to save research results across sessions? Install the Serena plugin:
> ```
> claude plugin install serena@claude-plugins-official
> ```
> Then restart Claude Code. Your future `/gr:research` results will be auto-saved and browsable via `/gr:recall`.
