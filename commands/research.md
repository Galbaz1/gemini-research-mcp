---
description: Deep research on any topic with evidence-tier labeling
argument-hint: <topic>
allowed-tools: mcp__plugin_gr_gemini-research__web_search, mcp__plugin_gr_gemini-research__research_deep, mcp__plugin_gr_gemini-research__research_plan, mcp__plugin_gr_gemini-research__research_assess_evidence
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
