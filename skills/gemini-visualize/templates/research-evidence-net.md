# Research Evidence Network Template

Generate an interactive evidence network from deep research results. This template maps research findings into a graph where nodes are claims/findings and edges represent evidential relationships, with evidence-tier coloring.

## Data Extraction

From the `research_deep` result (ResearchReport), extract:

### Nodes
- **Findings** → one node per finding (use the `claim` field as label)
- **Open questions** → one node per open question (styled differently — dashed border)
- **Sources** → optionally show as small satellite nodes connected to the findings they support
- **Key terms** → extract significant terms from executive_summary that aren't already findings

### Edges
From the findings structure:
- **"supports"** — `supporting` sources → finding node (green edge)
- **"contradicts"** — `contradicting` sources → finding node (red edge)
- **"related to"** — findings that share sources or reasoning chains
- **"leads to"** — one finding's conclusion feeds into another's premise
- **"questions"** — open question nodes connect to the findings they challenge

### Categories (Evidence Tiers)
Each finding node is colored by its evidence tier:
- **CONFIRMED** → `#4ecdc4` (teal) — solid border, full opacity
- **STRONG INDICATOR** → `#6bcb77` (green) — solid border, 90% opacity
- **INFERENCE** → `#ffd93d` (yellow) — solid border, 80% opacity
- **SPECULATION** → `#fb923c` (orange) — dashed border, 70% opacity
- **UNKNOWN** → `#ff6b6b` (coral) — dotted border, 60% opacity

Open questions use `#c084fc` (purple) with dashed borders.

## HTML Structure

Follow the same structural pattern as the video concept map template but with these differences:

### Controls
- **Evidence tier checkboxes** — one per tier, all checked by default. Unchecking hides nodes of that tier
- **Source toggle** — show/hide source satellite nodes
- **Confidence slider** — filter by confidence value (if available)
- **Search** — text input to highlight matching nodes
- **Generate Prompt** — builds a follow-up research prompt

### Layout
- Use a **hierarchical layout** rather than pure force-directed:
  - CONFIRMED findings at top
  - STRONG INDICATOR below
  - INFERENCE in the middle
  - SPECULATION lower
  - UNKNOWN at bottom
  - Open questions to the right side
- Within each tier, use force-directed positioning for horizontal spread
- Sources (if shown) orbit their parent findings as small satellite nodes

### Sidebar Detail Panel
When a finding node is selected, show:
- **Claim** (full text)
- **Evidence tier** with colored badge
- **Supporting evidence** (bullet list with source citations)
- **Contradicting evidence** (if any, in red)
- **Reasoning** (the reasoning chain from the finding)
- **Connected findings** (other nodes linked by edges)

## Prompt Generation

When "Generate Prompt" is clicked, build a research follow-up prompt:

```
I researched "[Topic]" and found these results:

Findings I want to verify further:
- [SPECULATION finding 1] — currently speculative
- [INFERENCE finding 2] — based on indirect evidence

Open questions to investigate:
- [Open Question 1]
- [Open Question 2]

Specific gaps:
- [UNKNOWN finding 1] needs more evidence

Please help me:
1. Find stronger evidence for the speculative findings
2. Investigate the open questions
3. Identify sources that could fill the evidence gaps
```

## Visual Design Notes

- Edge thickness varies by relationship strength (more shared sources = thicker)
- Edges curve slightly to avoid overlap (bezier with control points offset from midpoint)
- Animate evidence tier transitions when filtering (nodes fade rather than disappear)
- Cluster related findings visually (findings sharing 2+ sources should be placed closer)
- Executive summary appears as a fixed header bar above the graph (subtle, collapsible)

## Node Sizing

Size nodes by evidential weight:
- **Large** (radius 24): CONFIRMED findings with 3+ supporting sources
- **Medium** (radius 18): STRONG INDICATOR and INFERENCE findings
- **Small** (radius 12): SPECULATION, UNKNOWN, open questions
- **Tiny** (radius 8): Source satellite nodes (if shown)
