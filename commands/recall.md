---
description: Browse and recall past research, video notes, and analyses
argument-hint: [topic|category|fuzzy|unknown]
allowed-tools: Glob, Grep, Read
model: sonnet
---

# Recall: $ARGUMENTS

Browse saved results from previous `/gr:*` commands, including visualizations and knowledge states.

## Find the Memory Directory

Use `Glob` on `~/.claude/projects/*/memory/gr/` to find saved results. There may be results across multiple project directories — check all of them.

## Behavior

### If no arguments given (`$ARGUMENTS` is empty):

1. Use `Glob` with pattern `~/.claude/projects/*/memory/gr/**/analysis.md` to find all saved results
2. For each result, read the first 5 lines to get the title and check for visualization artifacts:
   - Check if `concept-map.html`, `evidence-net.html`, or `knowledge-graph.html` exists alongside `analysis.md`
   - Check if `screenshot.png` exists
3. Group by category and present as a clean list with visualization indicators:

   **Research** (`gr/research/`)
   - `topic-slug` — <first heading> 📊 (has evidence network)
   - `topic-slug-2` — <first heading>

   **Video Notes** (`gr/video/`)
   - `video-slug` — <first heading> 📊 (has concept map)

   **Video Chats** (`gr/video-chat/`)
   - `chat-slug` — <first heading> 📊 (has concept map)

   **Analyses** (`gr/analysis/`)
   - `source-slug` — <first heading> 📊 (has knowledge graph)

   Legend: 📊 = interactive visualization available

4. Show the total count and invite the user to:
   - Pick one to read in detail
   - Give a topic to filter
   - Use `fuzzy` or `unknown` to find knowledge gaps

### If arguments match a category (`research`, `video`, `video-chat`, `analysis`):

1. Use `Glob` with pattern `~/.claude/projects/*/memory/gr/$ARGUMENTS/*/analysis.md`
2. List all results in that category with their titles and viz indicators
3. Read the first heading and YAML frontmatter of each file

### If arguments are "fuzzy" or "unknown":

**Knowledge state filtering** — shows concepts matching the requested state across ALL analyses.

1. Use `Glob` to find all `gr/**/analysis.md` memory files
2. Read the YAML frontmatter of each file looking for `concepts:` with matching `state:`
3. Collect all matching concepts and present grouped by source:

   **Concepts you're fuzzy on:**

   From `gr/video/boris-cherny/`:
   - **Latent Demand** (timestamp: 12:15) — "the idea that making something easier increases total demand"
   - **Jevons Paradox** (timestamp: 30:26) — "economic principle where efficiency gains increase consumption"

   From `gr/research/ai-code-generation/`:
   - **Benchmark Saturation** — "when models plateau on existing benchmarks"

4. For each concept, show:
   - Name and brief description
   - Source analysis (with link to the full analysis)
   - Timestamp (for video sources)
   - Suggest: "Want to dive deeper into any of these? I can re-analyze the source."

5. If no concepts match the requested state, report that and suggest the user review their analyses to update knowledge states.

### If arguments are a keyword:

1. Use `Glob` to find all `gr/**/analysis.md` memory files
2. Use `Grep` to search file contents for "$ARGUMENTS"
3. If matches found:
   - List them with the matching context (2 lines around the match)
   - Show viz indicators for each result
4. If a single match, read and present the full content directly

### Reading a result:

When the user picks a result (by name or number):

1. Use `Read` to show the full `analysis.md` content. Present it cleanly — it's already well-structured markdown.
2. Check for companion artifacts and report:
   - **Visualization**: If an HTML file exists, tell the user the path and offer: "Open the interactive visualization? I can serve it in a browser."
   - **Screenshot**: If `screenshot.png` exists, note it: "Screenshot available at `<path>/screenshot.png`"
3. If the result has YAML frontmatter with `concepts:`, show a brief knowledge state summary:
   - X concepts known, Y fuzzy, Z unknown
   - "Use `/gr:recall fuzzy` to see all fuzzy concepts across analyses"

## Opening Visualizations

If the user asks to open/view a visualization:

1. Note: This recall command doesn't have Playwright tools. Suggest the user open the HTML file directly:
   - "Open `<path>/concept-map.html` in your browser"
   - Or suggest re-running the original analysis command which has Playwright access

## Management

If the user asks to delete a result, confirm first, then note the directory path so they can remove it manually: `rm -rf <path>`. Commands cannot delete memory files.

If the user wants to update a knowledge state manually, they can edit the YAML frontmatter in `analysis.md`, or use the interactive visualization to cycle states and paste the generated prompt.
