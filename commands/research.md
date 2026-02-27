---
description: Deep research on any topic with evidence-tier labeling
argument-hint: <topic>
allowed-tools: mcp__gemini-research__web_search, mcp__gemini-research__research_deep, mcp__gemini-research__research_plan, mcp__gemini-research__research_assess_evidence, Write, Glob, Read
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

After presenting results, auto-save to the project's memory directory for future reference.

1. Determine the memory directory: find the `.claude/` project memory path for the current working directory. The standard location is `~/.claude/projects/<project-key>/memory/gr/research/`. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
2. Generate a slug from the topic: lowercase, hyphens, no special chars, max 50 chars (e.g., "impact of mcp on ai agents" → `impact-of-mcp-on-ai-agents`)
3. Use `Write` to save the file at `<memory-dir>/gr/research/<slug>.md`:

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

4. Confirm: **Saved to `gr/research/<slug>`** — browse past research with `/gr:recall research`
