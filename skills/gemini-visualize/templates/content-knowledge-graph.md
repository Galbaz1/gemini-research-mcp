# Content Knowledge Graph Template

Generate an interactive knowledge graph from content analysis results. This template maps entities, relationships, and key points into a navigable graph.

## Data Extraction

From the `content_analyze` result (ContentResult or custom schema), extract:

### Nodes
- **Entities** → one node per entity from the `entities` array (people, orgs, concepts, technologies)
- **Key points** → one node per key point (larger, rectangular shape to distinguish from entities)
- **Title/source** → a central "anchor" node representing the content itself

### Edges
Infer relationships from content:
- **"mentions"** — key point node → entity it references
- **"authored by"** / **"created by"** — content → person/org
- **"uses"** / **"implements"** — concept → technology/tool
- **"part of"** — sub-concept → parent concept
- **"contrasts with"** — opposing entities or ideas
- **"defined as"** — entity → its definition (shown as edge label)

### Categories (Entity Types)
Color nodes by entity type:
- **Person** → `#4ecdc4` (teal) — circle shape
- **Organization** → `#4d96ff` (blue) — rounded rectangle
- **Concept** → `#c084fc` (purple) — circle shape
- **Technology** → `#6bcb77` (green) — hexagon shape
- **Location** → `#fb923c` (orange) — diamond shape
- **Event** → `#ffd93d` (yellow) — circle shape
- **Key Point** → `#e0e0e0` (light gray) — rounded rectangle, larger

## HTML Structure

Follow the same structural pattern as the video concept map template but with these differences:

### Controls
- **Entity type checkboxes** — one per entity type, all checked by default
- **Importance threshold slider** — filter out low-importance entities (based on mention frequency)
- **Depth selector** — 1 (entities only), 2 (+ relationships), 3 (+ key points) — controls visual complexity
- **Search** — text input to highlight matching nodes
- **Generate Prompt** — builds an extraction refinement prompt

### Layout
- **Radial layout** from the central content node:
  - Content anchor in center
  - Key points in first ring
  - Primary entities (most connected) in second ring
  - Secondary entities in outer ring
- Force-directed within each ring for spacing
- Edges route between rings with curved paths

### Sidebar Detail Panel
When a node is selected, show:
- **Entity name** and type with colored badge
- **Description** (from content context, 1-2 sentences)
- **Mentions** (count of appearances in the content)
- **Relationships** (list of connected nodes with edge labels)
- **Source quote** (the most relevant excerpt from the content mentioning this entity)
- **Quality assessment** (if available from ContentResult)

## Prompt Generation

When "Generate Prompt" is clicked, build an extraction refinement prompt:

```
I analyzed "[Content Title]" ([source]).

Entities I want more detail on:
- [Selected Entity 1] — currently described as "[brief description]"
- [Selected Entity 2] — relationship to [Entity 3] unclear

Relationships to clarify:
- How does [Entity A] relate to [Entity B]?
- Is [Entity C] part of [Entity D] or separate?

Please re-analyze the content focusing on:
1. Deeper context for the selected entities
2. Clarifying the ambiguous relationships
3. Any entities or connections I might have missed
```

## Visual Design Notes

- Key point nodes are **wider** (pill-shaped) to accommodate longer labels
- Entity nodes use **shape coding** in addition to color (circle, hexagon, diamond, rectangle)
- The central content node is the largest, with a subtle glow effect
- On hover, highlight all edges connected to the hovered node (dim others to 20% opacity)
- Double-click a node to "focus" — re-centers the graph around that node and shows only 2-hop neighbors
- Importance is shown via node opacity (100% for high, 60% for low) in addition to the threshold filter

## Node Sizing

Size nodes by importance (mention frequency + edge count):
- **Central** (radius 32): The content anchor node
- **Large** (radius 24): Key points and primary entities (5+ mentions or connections)
- **Medium** (radius 18): Secondary entities (2-4 mentions)
- **Small** (radius 12): Tertiary entities (1 mention)

## Depth Levels

The depth selector controls visual complexity:
- **Level 1**: Show only entity nodes (no key points, no edge labels)
- **Level 2**: Add relationship edges with labels
- **Level 3**: Add key point nodes and their connections (full graph)

Default to Level 2 for most content. Use Level 3 for rich documents (10+ entities).
