# Video Explainer System

A system for generating high-quality explainer videos from technical documents. Transform research papers, articles, and documentation into engaging video content with automated narration and programmatic animations.

## Example Videos

- [World Models: The Missing Piece for AGI](https://youtu.be/FWGlRy1lPxM?si=mEd0YmE231VOPs4z)
- [How AI Learned to Reason: DeepSeek and o1 Explained](https://youtu.be/uUTTeGVB6z8)
- [How LLMs Actually Understand Images](https://youtu.be/PuodF4pq79g?si=4T0CV555qr89DSvY)
- [What Happens in 300ms Before AI Responds (Short)](https://youtube.com/shorts/Ctlvk5ALxxI)
- [The Trick That Let AI See (Short)](https://www.youtube.com/shorts/vwI_gD4OG4I)

## Features

### Content Pipeline
- **Multi-Format Input** - Parse Markdown, PDF documents, and web URLs
- **Script Generation** - Generate video scripts with visual cues and voiceover text
- **Text-to-Speech** - Integration with ElevenLabs and Edge TTS
- **Manual Voiceover** - Import your own recordings with Whisper transcription

### Visual Generation
- **Remotion Animations** - React-based programmatic video generation
- **AI Scene Generation** - Claude-powered scene component creation
- **Visual Refinement** - 4-phase quality improvement system

### Sound Design
- **Automated SFX** - Intelligent sound effect planning and generation
- **AI Background Music** - Generate ambient music using MusicGen
- **Audio Mixing** - Combine voiceover, SFX, and music

### Shorts & Distribution
- **Vertical Shorts** - 1080x1920 for YouTube Shorts, Reels, TikTok
- **TikTok-Style Captions** - Single-word captions with glow effects
- **Multiple Variants** - Generate different versions from same project

### Quality Assurance
- **Fact Checking** - Verify accuracy against source material
- **Feedback Processing** - Natural language feedback to file updates

## Architecture

```
Document → Parse → Analyze → Script → TTS → Storyboard → Animation → Video
                                       │         ↑
                                       │    (JSON schema)
                                       └─────────┘
                                    (word timestamps)
```

**Key Insight:** TTS generation happens BEFORE storyboard creation because we need audio timing (word-level timestamps) to sync visuals precisely to narration.

### Project Structure

```
video_explainer/
├── projects/                    # Self-contained video projects
│   └── <project>/               # Each project contains:
│       ├── config.json          # Project configuration
│       ├── input/               # Source documents (MD, PDF)
│       ├── script/              # Generated scripts
│       ├── narration/           # Scene narrations
│       ├── scenes/              # Remotion components (*.tsx)
│       ├── voiceover/           # Audio files (*.mp3)
│       ├── storyboard/          # Storyboard JSON
│       ├── music/               # Background music
│       ├── short/               # Shorts variants
│       └── output/              # Final videos
│
├── src/                         # Core pipeline code
│   ├── cli/                     # CLI commands
│   ├── ingestion/               # Document parsing
│   ├── script/                  # Script generation
│   ├── scenes/                  # Scene component generation
│   ├── audio/                   # TTS providers
│   ├── sound/                   # SFX system
│   ├── music/                   # MusicGen integration
│   ├── refine/                  # Refinement system
│   └── short/                   # Shorts generation
│
└── remotion/                    # Remotion project (React)
    ├── src/components/          # Reusable components
    ├── src/scenes/              # Scene compositions
    └── scripts/render.mjs       # Headless rendering
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- FFmpeg

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd video_explainer

# Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Remotion dependencies
cd remotion && npm install && cd ..
```

### Basic Workflow

```bash
# 1. Create a new project
python -m src.cli create my-video

# 2. Add source documents to projects/my-video/input/

# 3. Run the full pipeline
python -m src.cli generate my-video

# 4. Preview in Remotion Studio
cd remotion && npm run dev

# 5. Render final video
python -m src.cli render my-video
```

### Step-by-Step Pipeline

```bash
python -m src.cli script my-video        # Generate script from input docs
python -m src.cli narration my-video     # Generate scene narrations
python -m src.cli scenes my-video        # Generate Remotion components
python -m src.cli voiceover my-video     # Generate TTS audio
python -m src.cli storyboard my-video    # Create storyboard
python -m src.cli render my-video        # Render final video
```

## CLI Reference

### Project Management

```bash
python -m src.cli list                    # List all projects
python -m src.cli info <project>          # Show project details
python -m src.cli create <project_id>     # Create new project
```

### Generation Pipeline

```bash
# Full pipeline
python -m src.cli generate <project>              # Run all steps
python -m src.cli generate <project> --force      # Regenerate everything
python -m src.cli generate <project> --mock       # Use mock LLM/TTS

# Partial runs
python -m src.cli generate <project> --from scenes    # Start from step
python -m src.cli generate <project> --to voiceover   # Stop at step
```

### Individual Steps

```bash
python -m src.cli script <project>        # Generate script
python -m src.cli narration <project>     # Generate narrations
python -m src.cli scenes <project>        # Generate scene components
python -m src.cli voiceover <project>     # Generate audio
python -m src.cli storyboard <project>    # Create storyboard
python -m src.cli render <project>        # Render video
```

### Sound Design

```bash
python -m src.cli sound <project> analyze     # Preview detected moments
python -m src.cli sound <project> generate    # Generate SFX cues
python -m src.cli music <project> generate    # Generate background music
```

See [docs/SOUND.md](docs/SOUND.md) for detailed sound design documentation.

### Refinement

```bash
python -m src.cli refine <project> --phase analyze     # Gap analysis
python -m src.cli refine <project> --phase script      # Script refinement
python -m src.cli refine <project> --phase visual-cue  # Visual spec refinement
python -m src.cli refine <project> --phase visual      # AI visual inspection
```

See [docs/REFINEMENT.md](docs/REFINEMENT.md) for the 4-phase refinement process.

### Shorts Generation

```bash
python -m src.cli short generate <project>    # Full shorts pipeline
python -m src.cli render <project> --short    # Render the short
```

See [docs/SHORTS.md](docs/SHORTS.md) for shorts workflow and timing sync.

### Quality Assurance

```bash
python -m src.cli factcheck <project>                          # Verify accuracy
python -m src.cli feedback <project> add "Make text larger"    # Process feedback
```

### Rendering Options

| Preset | Resolution | Use Case |
|--------|------------|----------|
| 4k     | 3840x2160  | YouTube/Final |
| 1440p  | 2560x1440  | High quality |
| 1080p  | 1920x1080  | Default |
| 720p   | 1280x720   | Development |
| 480p   | 854x480    | Quick preview |

```bash
python -m src.cli render <project> -r 4k          # 4K render
python -m src.cli render <project> --fast         # Faster encoding
python -m src.cli render <project> --preview      # Quick preview
python -m src.cli render <project> --concurrency 8  # Thread count
```

See [docs/CLI.md](docs/CLI.md) for complete CLI reference with all options.

## Configuration

### Project Configuration (projects/*/config.json)

```json
{
  "id": "my-video",
  "title": "My Explainer Video",
  "video": {
    "resolution": { "width": 1920, "height": 1080 },
    "fps": 30,
    "target_duration_seconds": 180
  },
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "your-voice-id"
  },
  "style": {
    "background_color": "#0f0f1a",
    "primary_color": "#00d9ff"
  }
}
```

### Global Configuration (config.yaml)

```yaml
llm:
  provider: claude-code  # claude-code | mock | anthropic | openai
  model: claude-sonnet-4-20250514

tts:
  provider: mock  # mock | elevenlabs | edge
  voice_id: null

video:
  width: 1920
  height: 1080
  fps: 30
```

### Environment Variables

- `ANTHROPIC_API_KEY` - For Claude LLM provider
- `OPENAI_API_KEY` - For OpenAI LLM provider
- `ELEVENLABS_API_KEY` - For ElevenLabs TTS

## Development

### Remotion Studio

```bash
cd remotion
npm run dev
```

Opens at `http://localhost:3000` for previewing compositions.

### Creating Animation Components

```tsx
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export const MyComponent: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  return <div style={{ opacity }}>{title}</div>;
};
```

### Testing

```bash
# Python tests (1192 tests)
pytest tests/ -v
pytest tests/ -v -m "not slow"  # Skip network tests

# JavaScript tests (203 tests)
cd remotion && npm test
```

### Visual Style

Default theme for technical content:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Slate | `#0f0f1a` |
| Compute/Data | Cyan | `#00d9ff` |
| Memory | Orange | `#ff6b35` |
| Optimization | Green | `#00ff88` |
| Problems | Red | `#ff4757` |

Typography: Inter/SF Pro for text, JetBrains Mono for code

## Documentation

- [CLI Reference](docs/CLI.md) - Complete command reference with all options
- [Refinement System](docs/REFINEMENT.md) - 4-phase quality improvement process
- [Shorts Generation](docs/SHORTS.md) - Vertical video workflow and timing sync
- [Sound Design](docs/SOUND.md) - SFX system and AI music generation

## Dependencies

### Python
- pydantic, rich, pyyaml - Core utilities
- edge-tts - Microsoft Edge TTS
- pymupdf - PDF parsing
- transformers, torch - MusicGen AI music

### Node.js
- remotion, @remotion/renderer - Video rendering
- react - UI components
- vitest - Testing

### System
- FFmpeg - Video processing
- Node.js 20+ - Remotion runtime

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Remotion](https://remotion.dev/) - React-based video generation
- [ElevenLabs](https://elevenlabs.io/) - Text-to-Speech
- [MusicGen](https://github.com/facebookresearch/audiocraft) - AI music generation
- [FFmpeg](https://ffmpeg.org/) - Video processing
