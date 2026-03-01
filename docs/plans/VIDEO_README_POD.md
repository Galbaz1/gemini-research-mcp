# Production Order Document: video-research-mcp README Video

## 1. PROJECT OVERVIEW

| Field | Value |
|-------|-------|
| **Title** | video-research-mcp — One Install. Every Video Understood. |
| **Duration** | 60 seconds |
| **Format** | Animated explainer (motion graphics + terminal recordings) |
| **Resolution** | 1920x1080 (16:9) |
| **Frame Rate** | 30 fps |
| **Target Audience** | Developers and technical users already familiar with Claude Code / MCP ecosystem |
| **Tone** | Calm, confident, technical. "Senior engineer explaining to a peer." |
| **Narration Style** | Voiceover — direct, no filler, declarative sentences |
| **Music** | Minimal electronic; builds at architecture beat, drops at terminal beat |

---

## 2. TECHNICAL SPECS

| Spec | Value |
|------|-------|
| Resolution | 1920x1080 |
| Aspect Ratio | 16:9 |
| Frame Rate | 30 fps |
| Codec | H.264 (MP4 container) |
| Audio | AAC 48kHz stereo |
| Color Space | sRGB |
| Safe Area | 90% (172px margin each side for text) |
| Export | MP4 (primary), WebM (fallback) |

---

## 3. SCRIPT

6 beats, 148 words total narration. All corrections from accuracy review applied (see Section 8).

### Beat 1 — HOOK (0:00 - 0:05)

> "You just sat through a 45-minute conference talk. Now try finding that one command they showed at minute 23."

### Beat 2 — PROBLEM (0:05 - 0:15)

> "Videos are full of valuable information -- buried in noise, impossible to search, lost the moment you close the tab."

### Beat 3 — ARCHITECTURE (0:15 - 0:30)

> "Gemini 3.1 Pro understands video natively. Twenty-four MCP tools bring that power into Claude Code. Connect Weaviate, and everything gets stored -- searchable across sessions, across projects."

**Correction applied:** Original said "Weaviate stores everything...forever." Weaviate is an optional dependency. Revised wording makes the opt-in nature clear.

### Beat 4 — QUICK-START (0:30 - 0:42)

> "One npm install. Set your Gemini API key. Point it at any video. That's it -- standard Claude Code prerequisites apply."

**Correction applied:** Original implied only install + API key needed. Revised wording acknowledges that Claude Code prerequisites (Node.js, uv, etc.) are assumed.

### Beat 5 — CAPABILITIES (0:42 - 0:55)

> "Analyze videos with timestamps and concept maps. Run deep research with evidence grading via strong indicators. Have multi-turn conversations about any recording. And recall everything you've ever analyzed -- semantically."

**Correction applied:** Original referenced "Supported" evidence tier. The codebase uses "Strong Indicator" as the tier name.

### Beat 6 — CLOSE (0:55 - 1:00)

> "One install. Every video understood."

**Note:** Tagline uses acceptable marketing hyperbole per accuracy review.

---

## 4. STORYBOARD

### Global Style Guide

- **Fonts:** Inter (UI/narration text), JetBrains Mono (code/terminal)
- **Canvas:** 1920x1080, 30fps
- **Background:** #1a1a2e (deep navy)
- **Transitions:** All cuts use 8-frame (0.27s) ease-in-out unless noted
- **Motion principle:** Elements enter from slight offset (20-40px) with opacity fade; never pop in

---

### Beat 1 — HOOK (0:00 - 0:05)

**Shot type:** Single frame, centered text with subtle camera push

**Visual elements:**
- Full-screen dark background (#1a1a2e)
- YouTube-style progress bar at bottom, scrubbed to ~51% (minute 23 of 45)
- Cursor icon frantically scrubbing back and forth along the progress bar
- Timestamp text "23:14" pulses in red (#e94560) near the scrub head
- Thin white text above: "Where was that command...?"

**Animation:**
- 0:00-0:02 — Progress bar fades in from bottom (ease-out, 12 frames)
- 0:02-0:05 — Cursor scrubs left-right 3 times (ease-in-out, accelerating), timestamp pulses on each direction change
- Subtle 2% zoom-in on entire frame over 5 seconds (Ken Burns drift)

**Transition out:** Hard cut to Beat 2 on final scrub position

---

### Beat 2 — PROBLEM (0:05 - 0:15)

**Shot type:** Split-screen comparison, left vs right

**Visual elements:**
- **Left half (chaos):** Stack of overlapping browser tabs, partially visible video players, scattered sticky notes with illegible text. Desaturated, slight blur. Label: "Before" in Inter Light, 16px, #666666
- **Right half (order):** Clean terminal window with structured output — timestamps, headings, bullet points. Sharp, full color. Label: "After" in Inter Medium, 16px, #2a9d8f
- Divider: 2px vertical line, #333333, centered

**Animation:**
- 0:05-0:08 — Left half builds: tabs stack in one by one (stagger 4 frames each, ease-out), blur increases
- 0:08-0:10 — Pause; divider line draws top-to-bottom (ease-in-out, 8 frames)
- 0:10-0:13 — Right half builds: terminal window slides in from right (ease-out, 10 frames), text types in line by line (monospace typewriter, 40ms per character)
- 0:13-0:15 — Left half dims further (opacity 0.4), right half gains subtle glow border (#2a9d8f, 1px, 20% opacity)

**Transition out:** Right half expands to fill frame (ease-in-out, 8 frames), becoming the canvas for Beat 3

---

### Beat 3 — ARCHITECTURE (0:15 - 0:30)

**Shot type:** 3-layer build-up diagram, bottom to top

**Visual elements — 3 layers:**

1. **Layer 1 — Gemini 3.1 Pro** (bottom)
   - Rounded rectangle, fill #0f3460 (blue), border 1px #4a7ab5
   - Google Gemini logomark (small, top-left corner of box)
   - Label: "Gemini 3.1 Pro" in Inter SemiBold 20px, white
   - Subtitle: "Native video understanding" in Inter Light 14px, #aaaaaa

2. **Layer 2 — 24 MCP Tools** (middle)
   - Rounded rectangle, fill #533483 (purple), border 1px #8b6aaf
   - Grid of 24 small icons (4x6), each representing a tool category: magnifying glass (search), beaker (research), film strip (video), book (knowledge), gear (infra), globe (web)
   - Label: "24 MCP Tools" in Inter SemiBold 20px, white
   - Subtitle: "Claude Code integration" in Inter Light 14px, #aaaaaa

3. **Layer 3 — Weaviate** (top, with opt-in indicator)
   - Rounded rectangle, fill #2a9d8f (teal), border 1px dashed #6bcbbd
   - Dashed border signals "optional"
   - Small "[optional]" badge, top-right, Inter Light 11px, #2a9d8f on dark pill
   - Weaviate logomark (small, top-left corner of box)
   - Label: "Weaviate Knowledge Store" in Inter SemiBold 20px, white
   - Subtitle: "Semantic search across sessions" in Inter Light 14px, #aaaaaa

**Connecting elements:**
- Vertical arrows between layers, animated upward: thin (#ffffff, 1px), small chevron heads
- Data flow particles (2px dots) travel along arrows during build

**Animation:**
- 0:15-0:19 — Layer 1 slides up from bottom (ease-out, 12 frames), arrow draws upward
- 0:19-0:23 — Layer 2 slides in from right (ease-out, 12 frames), icon grid populates (stagger 2 frames per icon), arrow draws upward
- 0:23-0:27 — Layer 3 fades in (ease-in-out, 10 frames) with dashed border drawing on
- 0:27-0:30 — All three layers pulse once in unison (scale 1.0 -> 1.02 -> 1.0, ease-in-out), data particles flow upward continuously

**Music cue:** Synth pad builds from 0:15, reaches full volume at 0:23 (Layer 3 entry)

**Transition out:** Diagram shrinks to top-right corner (ease-in-out, 8 frames) while terminal window expands from bottom-left

---

### Beat 4 — QUICK-START (0:30 - 0:42)

**Shot type:** Fullscreen terminal with typed commands

**Terminal styling:**
- Window chrome: macOS-style title bar, dark (#252525), three dots (red/yellow/green)
- Background: #1a1a2e
- Font: JetBrains Mono 16px
- Prompt: `$` in #2a9d8f (teal), command text in #e8e8e8 (white)
- Output text: #888888 (gray)
- Cursor: block, blinking, #e94560 (red)

**Command sequence:**

```
$ npx video-research-mcp@latest
  ✓ Commands installed (3)
  ✓ Skills installed (2)
  ✓ MCP server configured

$ export GEMINI_API_KEY=your-key-here
  (no output)

$ claude "analyze this video: https://youtu.be/example"
  ▸ Calling video_analyze...
  ▸ 12 segments identified
  ▸ Key topics: deployment, CI/CD, Docker
```

**Animation:**
- 0:30-0:33 — Terminal window slides up (ease-out, 8 frames). Command 1 types in (typewriter, 30ms/char). Output appears line by line (stagger 6 frames)
- 0:34-0:36 — Command 2 types in. Cursor blinks twice after Enter
- 0:37-0:41 — Command 3 types in. Output lines appear with loading spinner animation (rotating ▸)
- 0:41-0:42 — Small footnote fades in at bottom: "Requires Node.js, Python 3.11+, uv" in Inter Light 12px, #666666

**Music cue:** Beat drops to near-silence at 0:30 (terminal focus), light pulse on each Enter keypress

**Transition out:** Terminal content blurs and slides left, capability cards enter from right

---

### Beat 5 — CAPABILITIES (0:42 - 0:55)

**Shot type:** 4 rapid-fire capability cards, each on screen for ~3 seconds

**Card design (shared):**
- Rounded rectangle (12px radius), dark fill (#222244), subtle border (#333366, 1px)
- Icon top-left (32x32), title right of icon, preview content below
- Cards are 480x300px, centered on 1920x1080 canvas

**Card sequence:**

**Card A — Video Analysis (0:42-0:45)**
- Icon: Film strip (#e94560)
- Title: "Video Analysis" in Inter SemiBold 18px
- Preview: Miniature timeline with colored segment blocks, timestamps below each. Small concept-map diagram (3 nodes, 2 edges) in bottom half

**Card B — Deep Research (0:45-0:48)**
- Icon: Beaker (#0f3460)
- Title: "Deep Research" in Inter SemiBold 18px
- Preview: Evidence card with tier badge "Strong Indicator" in green pill, source citation, confidence bar at 85%

**Card C — Multi-turn Sessions (0:48-0:51)**
- Icon: Chat bubbles (#533483)
- Title: "Multi-turn Sessions" in Inter SemiBold 18px
- Preview: Chat-style message bubbles (user/assistant alternating), "Session: video-abc" header, context indicator showing "42 min cached"

**Card D — Knowledge Store (0:51-0:55)**
- Icon: Book (#2a9d8f)
- Title: "Knowledge Store" in Inter SemiBold 18px
- Preview: Search bar with query "deployment patterns", 3 result snippets below with relevance scores, "[optional]" badge top-right

**Animation per card:**
- Enter: slide in from right + fade (ease-out, 6 frames)
- Hold: 2.5 seconds, subtle parallax on hover-like micro-movement
- Exit: slide left + fade (ease-in, 6 frames), overlapping with next card entry by 4 frames

**Music cue:** Light rhythmic pulse, one hit per card transition

**Transition out:** All cards fly outward to four corners (ease-in, 8 frames), revealing clean background

---

### Beat 6 — CLOSE (0:55 - 1:00)

**Shot type:** Centered tagline with GitHub CTA

**Visual elements:**
- Clean #1a1a2e background
- Line 1: "One install." in Inter Bold 48px, #ffffff, centered
- Line 2: "Every video understood." in Inter Bold 48px, #2a9d8f (teal), centered, 8px below Line 1
- Line 3 (after pause): GitHub icon + "github.com/..." in Inter Medium 20px, #888888, 40px below tagline
- Subtle radial gradient behind text (center: #222244, edge: #1a1a2e)

**Animation:**
- 0:55-0:56 — Line 1 fades in (ease-in-out, 8 frames)
- 0:56-0:57 — Line 2 fades in (ease-in-out, 8 frames)
- 0:57-0:58 — Pause; both lines settle
- 0:58-1:00 — GitHub CTA fades in from below (ease-out, 8 frames). Entire frame holds to end

**Music cue:** Final chord resolves, fade to silence by 1:00

---

## 5. AUDIO DIRECTION

### Narration

| Parameter | Value |
|-----------|-------|
| Voice | Male or female, mid-range, American English neutral accent |
| Pace | 150 words/minute (~148 words in 60s with pauses) |
| Tone | Calm authority. No excitement, no sales pitch. Statement of fact. |
| Pauses | 0.5s between beats, 0.3s after key phrases ("That's it.", "forever.") |
| Processing | Light compression, no reverb, subtle de-essing |

### Music

| Parameter | Value |
|-----------|-------|
| Genre | Minimal electronic / ambient tech |
| BPM | 90-100 |
| Key | Minor (suggest Am or Cm) |
| Dynamics | Quiet bed during Hook/Problem, builds at Architecture (0:15), drops at Quick-Start (0:30), light pulse at Capabilities (0:42), resolves at Close (0:55) |
| Instruments | Soft synth pad, sub bass (sparse), hi-hat (Capabilities only), piano note (Close resolve) |
| Volume | -18dB under narration, -12dB during pauses |
| License | Royalty-free or original composition |

### Sound Effects

| Cue | Timing | Description |
|-----|--------|-------------|
| Scrub whoosh | 0:02-0:05 (Beat 1) | Soft whoosh on each cursor direction change |
| Tab stack | 0:05-0:08 (Beat 2) | Subtle paper/card shuffle on each tab layer |
| Typewriter click | Beat 4 | Soft mechanical key click per character, volume -24dB |
| Enter key | Beat 4 (x3) | Slightly louder Return key sound |
| Card swoosh | Beat 5 (x4) | Quick air swoosh on each card transition |
| Resolve tone | 0:55 (Beat 6) | Single clean tone (A4, 440Hz, sine, 2s decay) |

---

## 6. VISUAL ASSETS LIST

Assets that must be created or sourced before production.

### Icons (32x32 SVG, stroke style, 2px weight)

| Icon | Color | Used In |
|------|-------|---------|
| Film strip | #e94560 | Beat 3 grid, Beat 5 Card A |
| Beaker | #0f3460 | Beat 3 grid, Beat 5 Card B |
| Chat bubbles | #533483 | Beat 3 grid, Beat 5 Card C |
| Book | #2a9d8f | Beat 3 grid, Beat 5 Card D |
| Magnifying glass | #e94560 | Beat 3 grid |
| Gear | #888888 | Beat 3 grid |
| Globe | #0f3460 | Beat 3 grid |

### Logos (sourced, must respect brand guidelines)

| Logo | Usage | Notes |
|------|-------|-------|
| Google Gemini | Beat 3, Layer 1 | Logomark only (no wordmark), white/monochrome variant |
| Weaviate | Beat 3, Layer 3 | Logomark only, white/monochrome variant |
| GitHub | Beat 6 | Invertocat, white |

### Terminal Recording

| Asset | Description |
|-------|-------------|
| Terminal mock | macOS-style window chrome, custom colors per spec |
| Cursor animation | Block cursor, blink rate 530ms, color #e94560 |

### Diagram Components

| Asset | Description |
|-------|-------------|
| Architecture layers (x3) | Rounded rectangles with fills per color spec |
| Connecting arrows | Thin white arrows with chevron heads, animated particles |
| Tool icon grid (4x6) | 24 small icons, mixed from icon set above |
| Concept map (Beat 5A) | 3 nodes + 2 edges, simple force-directed layout |
| Evidence card (Beat 5B) | "Strong Indicator" pill badge, confidence bar |
| Chat bubbles (Beat 5C) | User/assistant alternating style |
| Search results (Beat 5D) | Query bar + 3 result snippets with scores |

---

## 7. TYPOGRAPHY & COLOR

### Typography Scale

| Element | Font | Weight | Size | Line Height | Color |
|---------|------|--------|------|-------------|-------|
| Tagline (Beat 6) | Inter | Bold (700) | 48px | 56px | #ffffff / #2a9d8f |
| Section label | Inter | SemiBold (600) | 20px | 28px | #ffffff |
| Subtitle | Inter | Light (300) | 14px | 20px | #aaaaaa |
| Beat label ("Before"/"After") | Inter | Light (300) | 16px | 22px | #666666 |
| Footnote | Inter | Light (300) | 12px | 16px | #666666 |
| Terminal command | JetBrains Mono | Regular (400) | 16px | 24px | #e8e8e8 |
| Terminal output | JetBrains Mono | Regular (400) | 16px | 24px | #888888 |
| Terminal prompt (`$`) | JetBrains Mono | Regular (400) | 16px | 24px | #2a9d8f |
| Badge text | Inter | Light (300) | 11px | 14px | varies |

### Color Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Deep Navy (bg) | #1a1a2e | 26, 26, 46 | Primary background, all beats |
| Red Accent | #e94560 | 233, 69, 96 | Highlights, cursor, error states, Hook timestamp |
| Blue | #0f3460 | 15, 52, 96 | Gemini layer, research icon, secondary accent |
| Teal | #2a9d8f | 42, 157, 143 | Weaviate layer, terminal prompt, "After" label, tagline L2 |
| Purple | #533483 | 83, 52, 131 | MCP tools layer, sessions icon |
| White | #ffffff | 255, 255, 255 | Primary text |
| Light Gray | #e8e8e8 | 232, 232, 232 | Terminal command text |
| Mid Gray | #aaaaaa | 170, 170, 170 | Subtitles |
| Dark Gray | #888888 | 136, 136, 136 | Terminal output, GitHub CTA |
| Muted Gray | #666666 | 102, 102, 102 | Labels, footnotes |
| Card Fill | #222244 | 34, 34, 68 | Capability card background |
| Card Border | #333366 | 51, 51, 102 | Capability card border |
| Terminal Chrome | #252525 | 37, 37, 37 | Terminal title bar |
| Divider | #333333 | 51, 51, 51 | Beat 2 split-screen divider |

### Syntax Highlighting (Terminal)

| Token | Color | Example |
|-------|-------|---------|
| Command | #e8e8e8 | `npx`, `export`, `claude` |
| Argument | #2a9d8f | `video-research-mcp@latest` |
| String | #e94560 | `"analyze this video..."` |
| Output check | #2a9d8f | `✓` |
| Output text | #888888 | `Commands installed (3)` |
| Spinner | #e94560 | `▸` |

---

## 8. ACCURACY NOTES

Three issues identified during technical review. All corrections applied in Section 3.

### Issue 1 — CRITICAL: Weaviate Optionality (Beat 3)

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Original | "Weaviate stores everything -- searchable across sessions, across projects, forever." |
| Problem | Weaviate is an optional dependency (`pip install video-research-mcp[agents]`). The knowledge store is disabled when `WEAVIATE_URL` is empty. Claiming it "stores everything...forever" is factually incorrect. |
| Fix applied | "Connect Weaviate, and everything gets stored -- searchable across sessions, across projects." |
| Visual fix | Beat 3 Layer 3 uses dashed border + "[optional]" badge. Beat 5 Card D includes "[optional]" badge. |

### Issue 2 — MEDIUM: Evidence Tier Name (Beat 5)

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Original | Referenced "Supported" as the evidence tier |
| Problem | The codebase uses "Strong Indicator" as the tier name for well-supported evidence |
| Fix applied | Changed to "strong indicators" in narration. Beat 5 Card B shows "Strong Indicator" pill badge. |

### Issue 3 — MEDIUM: Prerequisites Acknowledgment (Beat 4)

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Original | "One install. Set your API key. Point it at any video. That's it." |
| Problem | Implies zero prerequisites. In reality, Claude Code (which requires Node.js), Python 3.11+, and uv are prerequisites. |
| Fix applied | Narration: "One npm install. Set your Gemini API key. Point it at any video. That's it -- standard Claude Code prerequisites apply." Visual: footnote at 0:41 reads "Requires Node.js, Python 3.11+, uv" |

### Accepted — LOW: Tagline Hyperbole (Beat 6)

"One install. Every video understood." is marketing shorthand. Acceptable for a 60-second explainer aimed at developers who understand that "every" is aspirational.

---

## 9. PRODUCTION CHECKLIST

Ordered steps to produce the final video.

- [ ] **Pre-production**
  - [ ] Source or create all icons (7 SVG icons per asset list)
  - [ ] Obtain logo assets (Gemini, Weaviate, GitHub) in white/monochrome
  - [ ] Install fonts: Inter (Google Fonts), JetBrains Mono (JetBrains)
  - [ ] Set up project at 1920x1080, 30fps, sRGB
  - [ ] Create color swatches and typography presets

- [ ] **Asset creation**
  - [ ] Build terminal mock component (reusable across Beat 4)
  - [ ] Build architecture diagram layers (Beat 3)
  - [ ] Build capability card template (Beat 5)
  - [ ] Create concept map mini-diagram (Beat 5A)
  - [ ] Create evidence card with "Strong Indicator" badge (Beat 5B)
  - [ ] Create chat bubble layout (Beat 5C)
  - [ ] Create search results layout with "[optional]" badge (Beat 5D)

- [ ] **Animation**
  - [ ] Beat 1: Progress bar + cursor scrub animation
  - [ ] Beat 2: Split-screen build (chaos left, order right)
  - [ ] Beat 3: 3-layer architecture build with arrows and particles
  - [ ] Beat 4: Terminal typewriter with 3 command sequences
  - [ ] Beat 5: 4 capability cards with staggered enter/exit
  - [ ] Beat 6: Tagline fade-in + GitHub CTA
  - [ ] All transitions between beats (8-frame ease-in-out)

- [ ] **Audio**
  - [ ] Record or synthesize narration (148 words, ~60s)
  - [ ] Source or compose background music (minimal electronic, 90-100 BPM)
  - [ ] Create/source sound effects (6 cues per SFX table)
  - [ ] Mix: narration -0dB, music -18dB under voice / -12dB in gaps, SFX -24dB to -18dB
  - [ ] Master to -1dB peak, -14 LUFS integrated

- [ ] **Assembly**
  - [ ] Sync narration to beat timings
  - [ ] Sync music dynamics to beat structure
  - [ ] Place sound effects at specified cue points
  - [ ] Review all text for typos and accuracy

- [ ] **Quality check**
  - [ ] Verify all 3 accuracy corrections are reflected in visuals and narration
  - [ ] Check "[optional]" badge appears on Weaviate layer (Beat 3) and Knowledge Store card (Beat 5D)
  - [ ] Confirm "Strong Indicator" (not "Supported") on evidence card (Beat 5B)
  - [ ] Confirm prerequisites footnote appears at 0:41 (Beat 4)
  - [ ] Test playback at 1x — narration fits within beat windows
  - [ ] Check color contrast (WCAG AA minimum for all text)
  - [ ] Preview on dark and light monitors

- [ ] **Export**
  - [ ] Export MP4 (H.264, AAC 48kHz stereo)
  - [ ] Export WebM fallback
  - [ ] Generate thumbnail (Beat 6 frame, 1280x720)
  - [ ] Write video description with timestamps for each beat
