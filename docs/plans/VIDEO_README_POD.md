# Production Order Document — README Video

> **Title:** Multimodal Research Intelligence for Claude Code
> **Duration:** ~90 seconds (~215 words narration)
> **Format:** 1920x1080, 30fps, H.264, stereo audio
> **Target audience:** Developers and researchers who use Claude Code
> **Tone:** Calm, confident, peer-to-peer. Not a product launch — a tool demo by someone who built it for themselves.

---

## 1. Script

### BEAT 1 — HOOK (0:00–0:08)

**Visual:** Dark background (#1a1a2e). Kinetic typography, word-by-word slam. Split into two frustrations, each landing with a subtle bass hit. Second line in accent red (#e94560).

> **NARRATION:** "You just sat through an hour-long Teams meeting with three presentations — and the critical insight was on a slide you can't find. YouTube is full of great tutorials. It's also full of garbage."

*(34 words, ~8 seconds)*

---

### BEAT 2 — THE GAP (0:08–0:18)

**Visual:** Split screen. LEFT: a wall of YouTube thumbnails blurring past, a Teams recording timeline being scrubbed endlessly, scattered notes. RIGHT: empty — just a blinking cursor in a Claude Code terminal. The gap is visual: one side is chaos, the other is waiting.

> **NARRATION:** "It takes ages to find the signal in the noise. And reading is fast — video is slow. Meanwhile, Claude — your favorite coding agent — doesn't process video. But Gemini 3.1 Pro does."

*(34 words, ~10 seconds)*

**Transition:** The Gemini sparkle icon materializes on the RIGHT side. The cursor types: `npx video-research-mcp@latest`. The chaos on the LEFT freezes.

---

### BEAT 3 — THE BRIDGE (0:18–0:30)

**Visual:** Architecture builds on the right side as the frozen chaos fades. Three layers appear progressively, each with a beat:

Layer 1: Gemini 3.1 Pro (sparkle icon + wordmark, pulsing in blue #0f3460)
Layer 2: 24 MCP tools fan out as 7 sub-server badges (video, research, content, search, youtube, infra, knowledge)
Layer 3: Weaviate knowledge store with 11 collection labels (dashed border, [optional] tag)

Animated arrows show data flowing: Gemini → tools → Claude Code (up), tools → Weaviate (down, dashed/optional).

> **NARRATION:** "So I built a bridge. Gemini understands video, documents, and the web natively. Twenty-four MCP tools bring that power straight into Claude Code. Connect Weaviate, and everything you learn gets stored — searchable across projects, across sessions."

*(38 words, ~12 seconds)*

---

### BEAT 4 — THE INSTALL (0:30–0:38)

**Visual:** Full-frame terminal. macOS chrome, dark theme (#0f0f1a). Architecture thumbnail persists at 20% opacity in top-left corner. Commands type in with "tak-tak-tak" rhythm. Cursor is block-style, #e94560.

```
~ $ npx video-research-mcp@latest
  ✓ 14 commands, 5 skills, 6 agents → ~/.claude/
  ✓ 3 MCP servers configured (uvx from PyPI)

~ $ export GEMINI_API_KEY="your-key"
```

> **NARRATION:** "One install. One API key. That's it."

*(8 words, ~3 seconds. Let the terminal breathe — the visual carries this beat.)*

**Note:** 5 seconds of silence after narration. Terminal output scrolls with satisfying checkmark animations.

---

### BEAT 5 — WHAT IT DOES (0:38–1:10)

Each capability gets its own full-width moment, sliding in from right. Not a grid — each one breathes.

**5A. Meeting recordings (0:38–0:46)**

Terminal:
```
/gr:video-chat ~/recordings/project-kickoff.mp4
> "Create meeting minutes in Dutch. Screenshot every shared screen."
```
Output appears: timestamped minutes, action items, a row of extracted frames below.

> **NARRATION:** "Point it at a meeting recording. Gemini watches the whole thing — timestamps, decisions, action items. It even extracts the slides."

*(22 words, ~8 seconds)*

---

**5B. YouTube analysis (0:46–0:52)**

Terminal:
```
/gr:video https://youtube.com/watch?v=...
```
Output: structured analysis with precise timestamps (real ones like 3:47, 11:27). A concept map visualization expands in the corner.

> **NARRATION:** "YouTube tutorials? Same thing. Precise timestamps, concept maps, and the comments analyzed in the background."

*(15 words, ~6 seconds)*

---

**5C. Research with evidence (0:52–0:58)**

Terminal:
```
/gr:research "HNSW index parameters for high-dimensional embeddings"
```
Output: findings with colored evidence tier tags — Confirmed (green), Strong Indicator (blue), Inference (purple), Speculation (red).

> **NARRATION:** "Deep research runs web search and Gemini analysis in parallel. Every finding gets an evidence tier — not just answers, but how much you should trust them."

*(27 words, ~6 seconds)*

---

**5D. Knowledge recall (0:58–1:06)**

Terminal:
```
/gr:recall "optimization"
```
Two-section output: Semantic Results (Weaviate hits with scores) + Filesystem Results. Then:
```
/gr:recall ask "what did I learn about HNSW tuning?"
```
AI-generated answer appears with source citations.

> **NARRATION:** "And nothing gets lost. Every analysis, every finding goes into a knowledge store. Weeks later, in a different project — you just ask."

*(23 words, ~8 seconds)*

---

**5E. Quick montage — the rest (1:06–1:10)**

Rapid 1-second cuts, no narration, just kinetic text labels:
- `/gr:analyze` → PDF entities extracted
- `/gr:research-doc` → multi-document evidence pipeline
- `/gr:search` → web search with citations
- `/gr:traces` → MLflow trace viewer

*(4 seconds, no narration — let the breadth speak for itself)*

---

### BEAT 6 — THE CLOSER (1:10–1:20)

**Visual:** All elements converge to center point. Repo URL fades in: `github.com/Galbaz1/video-research-mcp`. Tagline below. Install command in a subtle pill underneath.

> **NARRATION:** "One install. Gemini's eyes. Claude's brain. Your memory."

*(9 words, ~4 seconds)*

**Hold for 6 more seconds:** Subtle particle drift, breathing glow. Small "Open source · MIT license" in #888888 bottom-right.

---

### META-HUMOR (subtle, baked in — not narrated)

1. **The tool demos itself:** A video about a tool that analyzes videos. The viewer is watching a video about a tool that watches videos.
2. **Beat 5A uses a real meeting:** The demo is the developer's own recording — not stock footage.
3. **The concept map in 5B** was generated by the plugin being demonstrated.
4. **Beat 5D recalls Beat 5C:** The knowledge store finds the research from earlier in the same video — persistence demonstrated in real-time.
5. **If generated by the explainer pipeline:** Tiny closing credit: "Made with /ve:explainer" — the plugin made its own promo.

---

## 2. Audio Direction

### Narration
- **Voice:** ElevenLabs, voice ID `WAppqUXeqDqXjNTaQxG9`
- **Settings:** stability=0.45, similarity_boost=0.75, speed=1.0
- **Tone:** Senior engineer explaining to a peer over coffee. Not a keynote.
- **Total narration:** ~215 words at measured pace

### Music
- **Style:** Minimal electronic ambient, 90-100 BPM
- **Dynamics:**
  - 0:00–0:08: Sparse tension (single pad + subtle bass)
  - 0:08–0:18: Quiet under problem statement
  - 0:18–0:30: Builds with architecture reveal (add arpeggiated synth)
  - 0:30–0:38: Near-silence for terminal (only keystroke SFX)
  - 0:38–1:06: Steady beat under capability demos
  - 1:06–1:10: Quick pulse for montage
  - 1:10–1:20: Single sustained chord, fading

### Sound Effects

| Cue | Time | Sound |
|-----|------|-------|
| Word slams | 0:00–0:05 | Subtle bass hit per word |
| Chaos blur | 0:08 | Soft whoosh |
| Gemini appear | 0:16 | Crystalline chime |
| Layer builds | 0:18, 0:22, 0:25 | Soft bass hit per layer |
| Terminal keys | 0:30–0:38 | Mechanical keyboard clicks |
| Checkmarks | 0:32, 0:33 | Soft "ping" |
| Montage cuts | 1:06–1:10 | Quick swoosh per cut |
| Closer convergence | 1:10 | Reverse cymbal swell |

---

## 3. Visual Style

### Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Background | `#1a1a2e` | All frames |
| Signal Red | `#e94560` | Highlights, timestamps, cursor |
| Deep Blue | `#0f3460` | Gemini layer, links |
| Teal | `#2a9d8f` | Terminal prompts, success |
| Purple | `#533483` | Weaviate, dividers |
| Dark Panel | `#16213e` | Cards, tool badges |
| Terminal BG | `#0f0f1a` | Terminal window fill |

### Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Hero kinetic text | Inter | Bold | 48pt |
| Terminal commands | JetBrains Mono | Regular | 18pt |
| Architecture labels | Inter | Bold | 24pt |
| Closing title | JetBrains Mono | Bold | 56pt |
| Closing tagline | Inter | Regular | 24pt |
| Evidence tier tags | Inter | Bold | 12pt (pill badges) |

---

## 4. Accuracy Notes

### Verified Against Codebase
- 24 MCP tools across 7 sub-servers ✓
- Gemini 3.1 Pro is default model (`gemini-3.1-pro-preview`) ✓
- `npx video-research-mcp@latest` correct install ✓
- Weaviate is optional — script uses opt-in language ✓
- Evidence tiers: Confirmed, Strong Indicator, Inference, Speculation ✓
- 11 Weaviate collections ✓
- Multi-turn sessions via video_create_session/video_continue_session ✓
- Knowledge search: hybrid, semantic, keyword with optional Cohere reranking ✓

### Corrections Applied
1. Weaviate presented as opt-in ("Connect Weaviate, and...")
2. Evidence tier "Supported" → "Strong Indicator"
3. Model is Gemini 3.1 Pro (not 1.5)

---

## 5. Production Checklist

### Pre-production
- [ ] Record/select real meeting recording for Beat 5A
- [ ] Run `/gr:video` on YouTube tutorial, capture real output for 5B
- [ ] Run `/gr:research`, capture evidence tier output for 5C
- [ ] Run `/gr:recall` semantic + ask mode for 5D
- [ ] Capture 4 tool outputs for Beat 5E montage
- [ ] Export architecture diagram as SVG

### Audio
- [ ] Generate narration via ElevenLabs (voice `WAppqUXeqDqXjNTaQxG9`)
- [ ] Review pacing — Beat 4 needs 5s terminal-only gap
- [ ] Source background music (minimal electronic, 90-100 BPM)
- [ ] Record/source 8 SFX cues

### Visual production
- [ ] Kinetic typography (Beat 1)
- [ ] Split-screen composition (Beat 2)
- [ ] 3-layer architecture build (Beat 3)
- [ ] Terminal typing sequences (Beats 4, 5A-5D)
- [ ] Rapid montage (Beat 5E)
- [ ] Closing lockup (Beat 6)

### Assembly & export
- [ ] Sync narration to visuals
- [ ] Mix music (-12dB under voice)
- [ ] Place SFX at cue points
- [ ] Render 1080p H.264 + WebM fallback
- [ ] Generate poster frame from Beat 6
- [ ] Embed in README
