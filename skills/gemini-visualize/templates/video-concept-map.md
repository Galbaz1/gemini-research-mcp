# Video Concept Map Template

Generate an interactive concept map from video analysis results. This template maps video content into an explorable knowledge graph with click-to-cycle knowledge states.

## Data Extraction

From the `video_analyze` result (VideoResult or custom schema), extract:

### Nodes
- **Key points** → one node per major point (use the text as label, truncate to ~40 chars)
- **Topics** → one node per topic (these become category headers too)
- **Timestamps** → attach to the most relevant node as metadata (shown in detail panel)
- **People/speakers** → nodes if multiple speakers or notable figures mentioned
- **Tools/products** → nodes if technical content (commands, libraries, frameworks)

### Edges
Infer relationships between nodes:
- **"builds on"** — point A is prerequisite for point B
- **"example of"** — specific instance illustrates a broader concept
- **"contradicts"** — tension or disagreement between ideas
- **"enables"** — one concept makes another possible
- **"related to"** — general association (use sparingly, prefer specific types)

### Categories
Cluster nodes into 3-7 categories based on topic groupings:
- Example for a tech talk: "Core Thesis", "Technical Details", "Predictions", "Advice", "Examples"
- Example for a tutorial: "Setup", "Core Concepts", "Advanced Patterns", "Troubleshooting"
- Assign a distinct color to each category from this palette:
  - `#4ecdc4` (teal), `#ff6b6b` (coral), `#ffd93d` (yellow), `#6bcb77` (green)
  - `#4d96ff` (blue), `#c084fc` (purple), `#fb923c` (orange)

## HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Video Title] — Concept Map</title>
  <style>
    /* Dark theme base */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0a0a0f; color: #e0e0e0; font-family: system-ui, -apple-system, sans-serif; overflow: hidden; }

    /* Canvas fills viewport */
    #canvas { width: 100vw; height: 100vh; display: block; cursor: grab; }
    #canvas.dragging { cursor: grabbing; }

    /* Sidebar detail panel */
    #sidebar { position: fixed; right: 0; top: 0; width: 360px; height: 100vh;
      background: #12121a; border-left: 1px solid #2a2a3a; transform: translateX(100%);
      transition: transform 0.3s ease; padding: 24px; overflow-y: auto; z-index: 10; }
    #sidebar.open { transform: translateX(0); }

    /* Legend (top-left) */
    #legend { position: fixed; left: 16px; top: 16px; background: #12121a;
      border: 1px solid #2a2a3a; border-radius: 8px; padding: 12px 16px; z-index: 5; }

    /* Controls (bottom-center) */
    #controls { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
      background: #12121a; border: 1px solid #2a2a3a; border-radius: 8px;
      padding: 8px 16px; display: flex; gap: 12px; align-items: center; z-index: 5; }

    /* Knowledge state badge on nodes */
    .state-know { fill: #4ecdc4; }
    .state-fuzzy { fill: #ffd93d; }
    .state-unknown { fill: #ff6b6b; }

    /* Search input */
    #search { background: #1a1a2a; border: 1px solid #3a3a4a; border-radius: 4px;
      color: #e0e0e0; padding: 6px 12px; font-size: 14px; width: 200px; }
  </style>
</head>
<body>
  <canvas id="canvas"></canvas>
  <div id="legend"><!-- Category legend, clickable to filter --></div>
  <div id="controls">
    <input id="search" type="text" placeholder="Search concepts...">
    <button id="btn-prompt">Generate Prompt</button>
    <button id="btn-reset">Reset View</button>
  </div>
  <div id="sidebar"><!-- Node detail panel --></div>

  <script>
    // === STATE ===
    const state = {
      nodes: [ /* { id, label, category, description, timestamp, state: 'unknown', x, y, vx, vy } */ ],
      edges: [ /* { source, target, type, label } */ ],
      categories: [ /* { name, color, visible: true } */ ],
      selected: null,        // node id
      dragging: null,        // node id being dragged
      camera: { x: 0, y: 0, zoom: 1 },
      search: '',
      simulation: { running: true, alpha: 1 }
    };

    // === POPULATE FROM ANALYSIS ===
    // (Generated dynamically based on video_analyze results)

    // === PHYSICS (force-directed layout) ===
    // Spring forces between connected nodes, repulsion between all nodes, centering force

    // === RENDERING ===
    // Draw edges as curves with labels, nodes as circles with category color,
    // knowledge state indicator (small badge), label below node

    // === INTERACTION ===
    // Click node → select, show sidebar, cycle knowledge state
    // Drag node → move it, pause simulation for that node
    // Scroll → zoom, drag background → pan
    // Search → dim non-matching nodes
    // Legend click → toggle category visibility

    // === PROMPT GENERATION ===
    // Reads nodes with state='fuzzy' or 'unknown', generates a targeted learning prompt
    // Format: "I'm studying [video title]. Help me understand these concepts I'm fuzzy on: ..."
  </script>
</body>
</html>
```

## Knowledge States

Each node has a `state` property that cycles on click:
- **Know** (`#4ecdc4` teal badge) — user understands this concept
- **Fuzzy** (`#ffd93d` yellow badge) — partially understood, wants to review
- **Unknown** (`#ff6b6b` coral badge) — doesn't understand yet

Default: all nodes start as `unknown`.

## Prompt Generation

When the user clicks "Generate Prompt", build a prompt from the current state:

```
I watched "[Video Title]" ([URL]).

Concepts I'm fuzzy on:
- [Fuzzy Node 1] (mentioned at [timestamp])
- [Fuzzy Node 2] (mentioned at [timestamp])

Concepts I don't understand:
- [Unknown Node 1] (mentioned at [timestamp])
- [Unknown Node 2] (mentioned at [timestamp])

Please explain these concepts, using examples from the video where possible.
Start with the ones I don't understand, then clarify the fuzzy ones.
```

Copy to clipboard and show a toast: "Prompt copied! Paste it into Claude."

## Presets

Generate 2-4 presets based on video sections (e.g., timestamp ranges):
- "Full Map" — show all nodes
- "[Topic Cluster 1]" — filter to first major topic
- "[Topic Cluster 2]" — filter to second major topic
- "Fuzzy + Unknown" — show only nodes needing review

Presets appear as buttons in the controls bar.

## Node Sizing

Size nodes by importance:
- **Large** (radius 24): Main thesis, core concepts (1-3 nodes)
- **Medium** (radius 18): Supporting concepts, key examples (5-10 nodes)
- **Small** (radius 12): Details, minor points (rest)

Importance is inferred from: frequency of mention, position in key_points (earlier = more important), whether it appears in the summary.
