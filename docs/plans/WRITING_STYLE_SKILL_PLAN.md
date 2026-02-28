# Plan: Writing-Style Skill for Plugin Pipeline

## Problem

All `/gr:*` commands produce `analysis.md` files written by Claude agents. These agents format Gemini's structured JSON output into prose. Without explicit writing guidance, the output reads like AI-generated documentation — inflated significance, promotional vocabulary, superficial -ing analyses, rule-of-three patterns, and bold-colon vertical lists.

The external `humanizer` skill (by @blader, based on Wikipedia's "Signs of AI writing") handles this well for on-demand editing, but we need it baked into the pipeline so every analysis output is clean by default.

## Key Finding

**Text generation is client-side, not server-side.** The MCP tools (Python) return structured JSON dicts. The commands (`commands/*.md`) instruct Claude how to format that JSON into `analysis.md`. Background agents (`agents/*.md`) also write prose that gets appended to analysis files.

This means the humanizer rules belong in a skill that commands and agents reference at write-time — not in the Python tools.

## Pipeline Text Generation Points

Every point where Claude writes user-facing prose to a file:

| Component | File | What it writes | When |
|-----------|------|---------------|------|
| `/gr:video` | `commands/video.md` | `analysis.md` (summary, key points, timestamps, relationship map) | Phase 2 + Phase 3 |
| `/gr:research` | `commands/research.md` | `analysis.md` (executive summary, findings by evidence tier, evidence network) | Phase 2 + Phase 3 |
| `/gr:analyze` | `commands/analyze.md` | `analysis.md` (summary, key points, entities, relationship map) | Phase 2 + Phase 3 |
| `/gr:video-chat` | `commands/video-chat.md` | `analysis.md` (session transcript, concept extraction) | Session end |
| comment-analyst | `agents/comment-analyst.md` | "Community Reaction" section appended to `analysis.md` | Background |
| researcher | `agents/researcher.md` | Research findings (when used as subagent) | On demand |

The visualizer agent generates HTML, not prose — skip.

## Implementation

### Step 1: Create `skills/writing-style/SKILL.md`

A compact skill (~60 lines) adapted from the humanizer's 24 patterns, filtered to only the patterns relevant to research/analysis output. The full humanizer is 440 lines with many examples — we don't need all that context for an always-on skill.

**Patterns to include** (most frequent in analysis output):

| # | Pattern | Watch words | Fix |
|---|---------|-------------|-----|
| 1 | Inflated significance | "pivotal", "testament", "crucial", "key role" | State what happened, not why it matters |
| 3 | Superficial -ing phrases | "highlighting...", "showcasing...", "ensuring..." | Delete the participle clause |
| 4 | Promotional language | "groundbreaking", "vibrant", "stunning", "renowned" | Use neutral descriptors |
| 5 | Vague attributions | "Experts argue", "Industry reports" | Name the source or drop the claim |
| 7 | AI vocabulary | "Additionally", "delve", "landscape", "tapestry", "foster" | Use plain English |
| 8 | Copula avoidance | "serves as", "stands as", "represents a" | Use "is", "are", "has" |
| 9 | Negative parallelisms | "It's not just... it's..." | State the positive directly |
| 10 | Rule of three | "innovation, inspiration, and industry insights" | Use however many items are actually needed |
| 15 | Bold-colon vertical lists | "**Topic:** The topic is..." | Write prose or use plain lists |
| 22 | Filler phrases | "In order to", "It is important to note that" | Cut to the verb |
| 24 | Generic positive conclusions | "The future looks bright" | End with a specific fact or next step |

**Patterns to skip** (not relevant to analysis output):
- #2 (media coverage notability) — not applicable to research analysis
- #6 (challenges sections) — our evidence tiers handle this properly
- #11 (synonym cycling) — rare in structured analysis
- #12 (false ranges) — rare
- #13 (em dash overuse) — we use `--` not `—`
- #14 (boldface overuse) — some bold is appropriate in analysis
- #16 (title case) — our heading templates are sentence case
- #17 (emojis) — already prohibited by project rules
- #18 (curly quotes) — not a problem in our pipeline
- #19 (collaborative artifacts) — commands don't produce chatbot text
- #20 (knowledge cutoff disclaimers) — Gemini doesn't do this
- #21 (sycophantic tone) — commands don't have this problem
- #23 (excessive hedging) — evidence tiers handle uncertainty explicitly

**Personality section** (adapted from humanizer):

Analysis output should sound like a competent researcher's notes, not a press release. Vary sentence length. Prefer concrete details ("the model achieved 94.2% accuracy on SQuAD") over vague claims ("the model demonstrated impressive results"). When evidence is uncertain, say so directly with the evidence tier — don't hedge with "potentially" and "might possibly".

**Skill metadata:**

```yaml
---
name: writing-style
description: |
  Writing quality rules for analysis output. Always active when writing
  analysis.md files. Prevents AI vocabulary, inflated significance,
  and promotional language. Adapted from the humanizer skill by @blader.
---
```

No `allowed-tools` — this is a passive skill (reference material, not an action skill).

### Step 2: Add writing-style reference to commands

Each command gets a single line added to its Phase 2 (write phase), before the `Write` instruction:

```markdown
**Writing style**: Follow the `writing-style` skill — no AI vocabulary, no inflated significance, concrete facts over vague claims. Vary sentence length.
```

**Files to edit:**

| File | Where to add |
|------|-------------|
| `commands/video.md` | Phase 2, before the `Write` to save `analysis.md` |
| `commands/research.md` | Phase 2, before the `Write` to save `analysis.md` |
| `commands/analyze.md` | Phase 2, before the `Write` to save `analysis.md` |
| `commands/video-chat.md` | Before session-end `Write` to save `analysis.md` |

### Step 3: Add writing-style reference to agents

Agents that produce prose appended to `analysis.md`:

| File | Where to add |
|------|-------------|
| `agents/comment-analyst.md` | Before the "Community Reaction" write instruction |
| `agents/researcher.md` | In the output format section |

### Step 4: Register in plugin installer

**`bin/lib/copy.js`** — add to `FILE_MAP`:
```js
'skills/writing-style/SKILL.md': 'skills/writing-style/SKILL.md',
```

Add to `CLEANUP_DIRS`:
```js
'skills/writing-style',
```

### Step 5: Update plugin counts

| File | Change |
|------|--------|
| `README.md` | Skills count: 3 → 4 in install section |
| `CLAUDE.md` | Update if skill count is mentioned |

## Commit

Single commit:
```
feat(plugin): add writing-style skill to humanize analysis output

Adapted from humanizer skill (@blader). 11 AI writing patterns
filtered for research/analysis context. Applied to all 4 commands
and 2 agents that write analysis.md prose.
```

## Verification

1. Read the skill file — rules should be clear, compact, actionable
2. Each command references the skill in its write phase
3. Each text-producing agent references the skill
4. `FILE_MAP` includes the skill, `CLEANUP_DIRS` includes the directory
5. `node bin/install.js --global` installs without errors
6. Run `/gr:research "any topic"` in test workspace — check `analysis.md` for AI patterns

## What This Does NOT Do

- Does not post-process existing files (use the external `humanizer` skill for that)
- Does not affect MCP tool output (that's structured JSON, not prose)
- Does not affect visualizer HTML generation
- Does not change how Gemini itself generates — it only governs how Claude formats Gemini's output into markdown

## Credit

Based on the [humanizer skill](https://github.com/blader/humanizer) by @blader, which is itself based on [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) maintained by WikiProject AI Cleanup.
