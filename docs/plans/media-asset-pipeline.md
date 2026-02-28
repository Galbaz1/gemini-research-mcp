# Media Asset Pipeline — Ontwerpdocument

> **Status:** Ontwerp
> **Datum:** 2026-02-28
> **Doel:** Video downloads en screenshots opslaan in Claude Memory, bestandspaden indexeren in Weaviate, zodat retrieval automatisch verwijst naar lokale bronbestanden.

---

## 1. Probleemstelling

### Huidige situatie

De video-analyse pipeline produceert rijke resultaten (samenvattingen, timestamps, concepten), maar er is een **broken link** tussen de analyse en het bronbestand:

| Aspect | Huidig gedrag | Probleem |
|--------|---------------|----------|
| **Video downloads** | `~/.cache/video-research-mcp/downloads/{id}.mp4` | Vluchtige cache, niet gekoppeld aan knowledge store |
| **Screenshots** | Bestaan niet als MCP-feature | Alleen de skills (`/gr:video`, `/gr:video-chat`) extraheren frames via ffmpeg naar project memory |
| **Weaviate opslag** | `source_url` bevat YouTube URL of origineel pad | Geen `local_filepath` — retrieval kan niet verwijzen naar lokaal bestand |
| **Recall flow** | `knowledge_search` geeft analyse-tekst terug | Geen manier om bronvideo opnieuw te openen zonder handmatig de URL te geven |

### Gewenst resultaat

```
Gebruiker: "Wat weet ik over context caching?"
                    │
                    ▼
        ┌───────────────────────┐
        │  knowledge_search()   │
        │  → VideoAnalyses hit  │
        │  → local_filepath:    │
        │    ~/.claude/.../     │
        │    video.mp4          │
        │  → screenshot_dir:    │
        │    ~/.claude/.../     │
        │    frames/            │
        └───────────┬───────────┘
                    │
                    ▼
        Claude herkent lokaal bestand
        → "Ik heb deze video lokaal. Wil je er opnieuw mee chatten?"
        → video_create_session(file_path=<local_filepath>)
        → Kan ook screenshots tonen uit frames/
```

---

## 2. Architectuuroverzicht

### Dataflow — Huidige vs. Nieuwe Pipeline

```
HUIDIGE PIPELINE:
═══════════════════════════════════════════════════════════

  video_analyze(url)
       │
       ├── Gemini analyseert video (via URL of File API)
       ├── Resultaat → file cache (~/.cache/.../hash.json)
       ├── Resultaat → Weaviate (VideoAnalyses)
       │                  └── source_url: "https://youtube.com/..."
       └── (optioneel) download → ~/.cache/.../downloads/id.mp4
                                   └── NIET gelinkt aan Weaviate


NIEUWE PIPELINE:
═══════════════════════════════════════════════════════════

  video_analyze(url)
       │
       ├── Gemini analyseert video
       ├── Resultaat → file cache (ongewijzigd)
       │
       ├── Download → Claude Memory
       │      ~/.claude/projects/<project>/memory/gr/media/videos/{id}.mp4
       │
       ├── Screenshot extractie (optioneel, als timestamps beschikbaar)
       │      ~/.claude/projects/<project>/memory/gr/media/screenshots/{id}/
       │          ├── frame_0215.png
       │          ├── frame_0842.png
       │          └── manifest.json
       │
       └── Weaviate store (uitgebreid)
              VideoAnalyses:
                ├── source_url: "https://youtube.com/..."    (bestaand)
                ├── local_filepath: "~/.claude/.../video.mp4" (NIEUW)
                └── screenshot_dir: "~/.claude/.../frames/"   (NIEUW)
```

### Componenten die veranderen

```
┌─────────────────────────────────────────────────────────┐
│                    SCHEMA LAAG                           │
│                                                          │
│  weaviate_schema/collections.py                          │
│    └── VideoAnalyses: +local_filepath, +screenshot_dir   │
│    └── SessionTranscripts: +local_filepath               │
│    └── CallNotes: +local_filepath                        │
│    └── ContentAnalyses: +local_filepath                  │
│                                                          │
│  weaviate_client.py                                      │
│    └── _evolve_collection() handelt migratie automatisch │
├─────────────────────────────────────────────────────────┤
│                    STORE LAAG                             │
│                                                          │
│  weaviate_store/video.py                                 │
│    └── store_video_analysis(): +local_filepath,          │
│         +screenshot_dir params                           │
│                                                          │
│  weaviate_store/session.py                               │
│    └── store_session_turn(): +local_filepath param       │
│                                                          │
│  weaviate_store/calls.py                                 │
│    └── store_call_notes(): +local_filepath               │
│                                                          │
│  weaviate_store/content.py                               │
│    └── store_content_analysis(): +local_filepath         │
├─────────────────────────────────────────────────────────┤
│                    TOOL LAAG                              │
│                                                          │
│  tools/youtube_download.py                               │
│    └── download locatie: cache_dir → memory dir          │
│                                                          │
│  tools/video_core.py                                     │
│    └── analyze_video(): local_filepath doorgeven aan     │
│        store_video_analysis()                            │
│                                                          │
│  tools/video.py                                          │
│    └── video_analyze: download + filepath tracking       │
│    └── video_create_session: filepath tracking           │
│    └── _download_and_cache: target dir wijzigen          │
├─────────────────────────────────────────────────────────┤
│                    SKILL LAAG                             │
│                                                          │
│  commands/video.md                                       │
│    └── Screenshot extractie naar memory/gr/media/        │
│                                                          │
│  commands/video-chat.md                                  │
│    └── Frame extractie naar memory/gr/media/             │
│                                                          │
│  commands/recall.md                                      │
│    └── Toon local_filepath bij retrieval resultaten      │
│    └── Bied "Chat met video" aan wanneer bestand lokaal  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Opslagstructuur — Claude Memory

### Huidige `gr/` memory layout (referentie)

```
~/.claude/projects/<project-hash>/memory/
  └── gr/
      ├── video/<slug>/analysis.md          ← /gr:video output
      ├── video-chat/<slug>/analysis.md     ← /gr:video-chat output
      ├── research/<slug>/analysis.md       ← /gr:research output
      ├── analysis/<slug>/analysis.md       ← /gr:analyze output
      └── calls/<slug>.md                   ← call notes
```

### Nieuwe `gr/media/` structuur

```
~/.claude/projects/<project-hash>/memory/
  └── gr/
      ├── video/...                         ← ongewijzigd
      ├── video-chat/...                    ← ongewijzigd
      ├── research/...                      ← ongewijzigd
      ├── analysis/...                      ← ongewijzigd
      ├── calls/...                         ← ongewijzigd
      └── media/                            ← NIEUW
          ├── videos/
          │   ├── dQw4w9WgXcQ.mp4           ← YouTube video (video_id als naam)
          │   ├── a1b2c3d4e5f6.mp4          ← lokaal bestand (SHA-256[:16] hash)
          │   └── .manifest.json            ← index: id → {title, source_url, size_mb, downloaded_at}
          └── screenshots/
              ├── dQw4w9WgXcQ/
              │   ├── frame_0215.png
              │   ├── frame_0842.png
              │   └── manifest.json         ← {frames: [{timestamp, description, path}]}
              └── a1b2c3d4e5f6/
                  └── ...
```

### Overwegingen

| Vraag | Beslissing | Rationale |
|-------|-----------|-----------|
| Waarom `gr/media/` en niet `~/.cache/`? | Claude Memory is persistent en project-gebonden | Cache is vluchtig; memory overleeft `cache clear` en is per-project doorzoekbaar |
| Waarom niet `gr/video/<slug>/video.mp4`? | Eén video kan door meerdere analyses worden gebruikt | Deduplicatie: video_id/hash is de sleutel, meerdere analyses verwijzen naar hetzelfde bestand |
| Hoe groot worden de bestanden? | 720p max, gemiddeld ~50-200 MB per video | `yt-dlp` format beperking is al ingebouwd (`mp4[height<=720]`) |
| Wat als de memory dir niet gevonden wordt? | Fallback naar `~/.cache/video-research-mcp/downloads/` | MCP server draait headless — heeft geen project context. Skills (commands) bepalen de memory dir |
| Disk space management? | `.manifest.json` maakt opruiming eenvoudig | Gebruiker kan handmatig of via toekomstige tool opruimen |

---

## 4. Weaviate Schema Wijzigingen

### 4.1 VideoAnalyses — Twee nieuwe properties

**Bestand:** `src/video_research_mcp/weaviate_schema/collections.py` (regel 45-78)

```python
# NIEUW — toe te voegen na "sentiment" property (regel 74):
PropertyDef(
    name="local_filepath",
    data_type=["text"],
    description="Local filesystem path to downloaded video file",
    skip_vectorization=True,
    index_searchable=False,
),
PropertyDef(
    name="screenshot_dir",
    data_type=["text"],
    description="Local filesystem path to screenshot directory",
    skip_vectorization=True,
    index_searchable=False,
),
```

**Vectorisatie:** Nee — bestandspaden zijn geen semantisch doorzoekbare content.
**Indexing:** `index_searchable=False` — geen full-text search op paden nodig. `index_filterable=True` (default) — zodat we later kunnen filteren op "heeft lokaal bestand" (`local_filepath IS NOT NULL`).

### 4.2 SessionTranscripts — Eén nieuw property

**Bestand:** `src/video_research_mcp/weaviate_schema/collections.py` (regel 155-171)

```python
# NIEUW — toe te voegen na "turn_response" property:
PropertyDef(
    name="local_filepath",
    data_type=["text"],
    description="Local filesystem path to the session's video file",
    skip_vectorization=True,
    index_searchable=False,
),
```

### 4.3 CallNotes — Eén nieuw property

**Bestand:** `src/video_research_mcp/weaviate_schema/calls.py` (regel 12-39)

```python
# NIEUW — toe te voegen na "meeting_date" property:
PropertyDef(
    name="local_filepath",
    data_type=["text"],
    description="Local filesystem path to the call recording file",
    skip_vectorization=True,
    index_searchable=False,
),
```

### 4.4 ContentAnalyses — Eén nieuw property

**Bestand:** `src/video_research_mcp/weaviate_schema/collections.py` (regel 80-100)

```python
# NIEUW — toe te voegen na "quality_assessment" property:
PropertyDef(
    name="local_filepath",
    data_type=["text"],
    description="Local filesystem path to the analyzed content file",
    skip_vectorization=True,
    index_searchable=False,
),
```

### 4.5 Migratie

**Geen handmatige migratie nodig.** Het bestaande `_evolve_collection()` mechanisme in `weaviate_client.py` (regel 236-254) voegt automatisch nieuwe properties toe aan bestaande collecties:

```python
def _evolve_collection(cls, col_def: CollectionDef, col) -> None:
    existing_props = {p.name for p in col.config.get().properties}
    for prop_def in col_def.properties:
        if prop_def.name not in existing_props:
            col.config.add_property(...)  # ← automatisch bij server start
```

Zodra de schema-definities zijn bijgewerkt en de server herstart, worden de nieuwe velden automatisch toegevoegd aan de bestaande Weaviate collecties. Bestaande objecten krijgen lege waarden voor de nieuwe properties.

---

## 5. Store Function Wijzigingen

### 5.1 `store_video_analysis()` — Twee nieuwe parameters

**Bestand:** `src/video_research_mcp/weaviate_store/video.py` (regel 15-75)

**Huidige signature:**
```python
async def store_video_analysis(
    result: dict, content_id: str, instruction: str, source_url: str = ""
) -> str | None:
```

**Nieuwe signature:**
```python
async def store_video_analysis(
    result: dict,
    content_id: str,
    instruction: str,
    source_url: str = "",
    local_filepath: str = "",      # NIEUW
    screenshot_dir: str = "",      # NIEUW
) -> str | None:
```

**Properties dict uitbreiding** (na regel ~40):
```python
props = {
    # ... bestaande properties ...
    "local_filepath": local_filepath,      # NIEUW
    "screenshot_dir": screenshot_dir,      # NIEUW
}
```

**Backward-compatible:** default `""` — bestaande callers hoeven niet te veranderen.

### 5.2 `store_session_turn()` — Eén nieuwe parameter

**Bestand:** `src/video_research_mcp/weaviate_store/session.py` (regel 11-45)

**Huidige signature:**
```python
async def store_session_turn(
    session_id: str, video_title: str, turn_index: int, prompt: str, response: str
) -> str | None:
```

**Nieuwe signature:**
```python
async def store_session_turn(
    session_id: str,
    video_title: str,
    turn_index: int,
    prompt: str,
    response: str,
    local_filepath: str = "",      # NIEUW
) -> str | None:
```

### 5.3 `store_call_notes()` — Eén nieuwe parameter

**Bestand:** `src/video_research_mcp/weaviate_store/calls.py` (regel 11-46)

Het `notes` dict accepteert al willekeurige keys. Voeg `local_filepath` toe aan het properties dict:
```python
props = {
    # ... bestaande properties ...
    "local_filepath": notes.get("local_filepath", ""),  # NIEUW
}
```

### 5.4 `store_content_analysis()` — Eén nieuwe parameter

**Bestand:** `src/video_research_mcp/weaviate_store/content.py` (regel 12-48)

**Nieuwe signature:**
```python
async def store_content_analysis(
    result: dict, source: str, instruction: str, local_filepath: str = ""
) -> str | None:
```

### 5.5 Re-exports bijwerken

**Bestand:** `src/video_research_mcp/weaviate_store/__init__.py`

Geen wijzigingen nodig — de functies worden al via naam geëxporteerd. De nieuwe parameters zijn backward-compatible (default waarden).

---

## 6. Tool-Laag Wijzigingen

### 6.1 Download Locatie — `youtube_download.py`

**Bestand:** `src/video_research_mcp/tools/youtube_download.py`

**Probleem:** De MCP server draait headless en kent geen project-specifieke memory directory. De download functie moet daarom een `target_dir` parameter accepteren.

**Huidige code (regel 21-25):**
```python
def _download_dir() -> Path:
    d = Path(get_config().cache_dir) / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

**Wijziging — `download_youtube_video()` krijgt optionele `target_dir`:**
```python
async def download_youtube_video(
    video_id: str, target_dir: Path | None = None
) -> Path:
    """Download YouTube video. Uses target_dir if provided, else default cache dir."""
    if target_dir is None:
        target_dir = _download_dir()
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{video_id}.mp4"
    # ... rest ongewijzigd
```

**Rationale:** De server zelf gebruikt de default cache dir. De **skills** (commands) bepalen de memory dir en geven die door via het `file_path` pattern — ze downloaden niet zelf, maar weten wél waar het bestand terechtkomt.

> **Belangrijk inzicht:** De MCP server kan niet weten in welk Claude project de gebruiker werkt. De `local_filepath` die in Weaviate wordt opgeslagen wordt bepaald door de **caller** — de tool berekent het pad, de skill instrueert Claude om het juiste memory-pad te gebruiken.

### 6.2 `analyze_video()` — Filepath doorgeven aan store

**Bestand:** `src/video_research_mcp/tools/video_core.py` (regel 39-106)

**Huidige store call (regel 104-105):**
```python
from ..weaviate_store import store_video_analysis
await store_video_analysis(result, content_id, instruction, source_label)
```

**Nieuwe store call:**
```python
await store_video_analysis(
    result, content_id, instruction, source_label,
    local_filepath=local_filepath,
    screenshot_dir=screenshot_dir,
)
```

**`analyze_video()` signature uitbreiding:**
```python
async def analyze_video(
    contents: types.Content,
    instruction: str,
    content_id: str = "",
    source_label: str = "",
    output_schema: dict | None = None,
    thinking_level: str = "high",
    use_cache: bool = True,
    metadata_context: str = "",
    local_filepath: str = "",      # NIEUW
    screenshot_dir: str = "",      # NIEUW
) -> dict:
```

### 6.3 `video_analyze` tool — Download tracking

**Bestand:** `src/video_research_mcp/tools/video.py` (regel 112-195)

Na de analyse, als er een download is gemaakt (via `_download_and_cache` of direct), wordt het bestandspad meegegeven:

```python
# Na analyze_video(), voeg het pad van de gedownloade video toe aan het resultaat
result["local_filepath"] = str(download_path) if download_path else ""
```

### 6.4 `video_create_session` — Filepath bewaren in sessie

**Bestand:** `src/video_research_mcp/tools/video.py` (regel 249-344)

Het `SessionInfo` model (in `models/video.py`) krijgt een optioneel `local_filepath` veld:

```python
class SessionInfo(BaseModel):
    session_id: str
    status: str
    video_title: str
    source_type: str
    cache_status: str = ""
    download_status: str = ""
    cache_reason: str = ""
    local_filepath: str = ""       # NIEUW
```

Wanneer een video is gedownload (via `_download_and_cache`) of een lokaal bestand is gebruikt, wordt het pad meegegeven.

---

## 7. Screenshot Extractie Pipeline

### 7.1 Twee niveaus van screenshot-extractie

| Niveau | Waar | Wanneer | Hoe |
|--------|------|---------|-----|
| **Skill-niveau** | `commands/video.md`, `commands/video-chat.md` | Na analyse, als er timestamps zijn | ffmpeg via Bash tool (bestaand mechanisme) |
| **MCP-niveau** | Nieuwe module of uitbreiding van `video_core.py` | Na analyse, als lokaal bestand beschikbaar is | ffmpeg subprocess (nieuw) |

### 7.2 Huidig mechanisme (skill-niveau, referentie)

De skills extraheren al frames via ffmpeg. Uit `commands/video.md` (regel 92-134):

```
Phase 2.5: Extract Video Frames (local files only)

1. Parse [SCREENSHOT:MM:SS:description] markers uit analyse
2. ffmpeg -y -ss 00:MM:SS -i <video> -frames:v 1 -q:v 2 <output>.png
3. Vervang markers in analysis.md met embedded images
```

**Probleem:** Dit werkt alleen voor lokale bestanden, niet voor YouTube-downloads. En de screenshots gaan naar `gr/video/<slug>/frames/` — per-analyse, niet gedeeld.

### 7.3 Nieuwe aanpak — Gedeelde screenshot opslag

**Principe:** Screenshots horen bij de **video** (geïdentificeerd door `content_id`), niet bij een specifieke analyse. Meerdere analyses van dezelfde video delen dezelfde screenshots.

**Opslaglocatie:**
```
gr/media/screenshots/{content_id}/
├── frame_0215.png
├── frame_0842.png
└── manifest.json
```

**`manifest.json` formaat:**
```json
{
  "content_id": "dQw4w9WgXcQ",
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "video_title": "Example Video",
  "extracted_at": "2026-02-28T14:30:00Z",
  "frames": [
    {
      "timestamp": "02:15",
      "filename": "frame_0215.png",
      "description": "Architecture diagram showing data flow"
    },
    {
      "timestamp": "08:42",
      "filename": "frame_0842.png",
      "description": "Demo of CLI tool in terminal"
    }
  ]
}
```

### 7.4 Screenshot extractie flow

```
video_analyze(url, download=true)
       │
       ├── Download video → gr/media/videos/{id}.mp4
       ├── Gemini analyse → timestamps + [SCREENSHOT] markers
       │
       └── Screenshot extractie (als video lokaal beschikbaar):
           │
           ├── Parse timestamps uit analyse resultaat
           ├── ffmpeg extract per timestamp
           ├── Opslaan in gr/media/screenshots/{id}/
           ├── Schrijf manifest.json
           └── screenshot_dir → Weaviate (VideoAnalyses)
```

### 7.5 Overwegingen

| Vraag | Beslissing | Rationale |
|-------|-----------|-----------|
| MCP-tool of alleen skill? | **Beiden** — skill voor interactieve controle, MCP voor automatische extractie | Skills bepalen welke frames; MCP-tool kan automatisch key-frames extracten |
| Wat als ffmpeg niet geïnstalleerd is? | Graceful skip — `shutil.which("ffmpeg")` check | Zelfde patroon als `yt-dlp` check in `youtube_download.py` |
| Hoeveel frames? | 8-15 per video (bestaande skill-richtlijn) | Balans tussen bruikbaarheid en disk usage (~100-500 KB per frame) |
| YouTube vs. lokaal? | YouTube: alleen als gedownload. Lokaal: altijd mogelijk | ffmpeg kan niet van remote URLs extraheren |

---

## 8. Knowledge Retrieval — Wat verandert

### 8.1 Geen code-wijzigingen nodig in knowledge tools

De `knowledge_search`, `knowledge_fetch`, en `knowledge_related` tools retourneren **alle properties** van een Weaviate object via het `properties` dict in `KnowledgeHit`. Dit is generiek — nieuwe properties verschijnen automatisch.

**Uit `tools/knowledge/helpers.py`** — de `serialize()` functie converteert Weaviate objects naar dicts:
```python
def serialize(obj) -> dict:
    """Serialize a Weaviate object's properties to a JSON-safe dict."""
    # Iterates ALL properties, converts datetimes to ISO strings
```

Zodra `local_filepath` en `screenshot_dir` in het schema staan, komen ze automatisch mee in:
- `knowledge_search` → `results[].properties.local_filepath`
- `knowledge_fetch` → `properties.local_filepath`
- `knowledge_related` → `related[].properties.local_filepath`

### 8.2 Skill-niveau verrijking nodig

De **recall skill** (`commands/recall.md`) moet wél worden bijgewerkt om:

1. `local_filepath` te herkennen in retrieval resultaten
2. Een actie aan te bieden wanneer een video lokaal beschikbaar is
3. Screenshot paden te tonen wanneer beschikbaar

---

## 9. Skill Updates

### 9.1 `commands/recall.md` — Lokale assets herkennen

**Toevoegingen aan het keyword search resultaat presentatie (huidige regel 129-132):**

Na het tonen van Weaviate resultaten, controleer op `local_filepath`:

```markdown
**Semantic Results (Knowledge Store)**
Per hit: collection, score, summary
- Als `local_filepath` niet leeg is EN het bestand bestaat:
  → "📁 Video lokaal beschikbaar: `<pad>`"
  → "Chat ermee: `/gr:video-chat <local_filepath>`"
- Als `screenshot_dir` niet leeg is EN de directory bestaat:
  → "🖼️ Screenshots beschikbaar in `<pad>`"
```

**Toevoeging aan het "Reading a result" gedeelte (huidige regel 148-158):**

```markdown
### Lokale Assets

Bij het tonen van een volledig resultaat, controleer:
1. Als `local_filepath` aanwezig in properties:
   - Controleer of bestand bestaat (`Glob` of `Read`)
   - Zo ja: "Video is lokaal beschikbaar. Wil je ermee chatten?"
   - Zo nee: "Video was eerder gedownload maar bestand niet meer aanwezig."
2. Als `screenshot_dir` aanwezig:
   - Toon beschikbare frames met hun timestamps
   - Embed frames in de presentatie indien relevant
```

### 9.2 `commands/video.md` — Download naar memory

**Wijzigingen in Phase 2.5 (Frame extractie, huidige regel 92-134):**

De target directory verandert van `gr/video/<slug>/frames/` naar `gr/media/screenshots/{content_id}/`:

```markdown
## Phase 2.5: Extract Video Frames

### Voor lokale bestanden (bestaand, locatie-update):
1. Parse [SCREENSHOT:MM:SS:description] markers
2. Extract naar `<memory-dir>/gr/media/screenshots/<content_id>/`
3. Schrijf manifest.json
4. Verwijs in analysis.md naar relatief pad: `../../media/screenshots/<id>/frame_MMSS.png`

### Voor YouTube (NIEUW, als gedownload):
1. Controleer of video lokaal staat: `<memory-dir>/gr/media/videos/<video_id>.mp4`
2. Zo ja: zelfde extractie als lokale bestanden
3. Zo nee: skip met melding "Download video eerst voor frame extractie"
```

**Nieuwe stap na Phase 1 — Download naar memory:**

```markdown
## Phase 1.5: Download to Memory (YouTube only)

1. Als de video een YouTube URL is:
   a. Controleer of yt-dlp beschikbaar is
   b. Download naar `<memory-dir>/gr/media/videos/<video_id>.mp4`:
      ```bash
      yt-dlp --no-playlist -q -f "mp4[height<=720]/mp4/best[ext=mp4]" \
        -o "<memory-dir>/gr/media/videos/<video_id>.mp4" \
        "https://youtube.com/watch?v=<video_id>"
      ```
   c. Als download slaagt: noteer `local_filepath` voor Weaviate store
   d. Als download faalt: ga door zonder lokaal bestand

2. Update `.manifest.json` in de videos directory:
   ```json
   {
     "<video_id>": {
       "title": "<Video Title>",
       "source_url": "<youtube_url>",
       "size_mb": 142.5,
       "downloaded_at": "2026-02-28T14:30:00Z"
     }
   }
   ```
```

### 9.3 `commands/video-chat.md` — Filepath in sessie

**Wijzigingen in Session Setup (huidige regel 14-24):**

```markdown
## Session Setup

1. Bepaal input type en controleer of video al lokaal is:
   - YouTube URL: check `<memory-dir>/gr/media/videos/<video_id>.mp4`
     - Als lokaal: gebruik `video_create_session(file_path=<lokaal pad>)`
       → "Video gevonden in memory — sessie gebruikt lokaal bestand (sneller + cached)"
     - Als niet lokaal: vraag download (bestaand AskUserQuestion)
   - Lokaal bestand: gebruik direct (ongewijzigd)
```

**Wijzigingen in Frame Extraction (huidige regel 63-87):**

```markdown
## Frame Extraction Support

Dezelfde wijziging als video.md:
- Frames naar `gr/media/screenshots/<content_id>/` in plaats van `gr/video-chat/<slug>/frames/`
- Gedeelde screenshots tussen analyses en chatsessies
```

### 9.4 `skills/video-research/SKILL.md` — Documentatie

De skill documentatie moet worden bijgewerkt om:
- `local_filepath` veld te documenteren als return-waarde
- `screenshot_dir` te documenteren
- Het nieuwe memory-opslagpatroon te beschrijven

---

## 10. Implementatieplan — Volgorde

### Fase 1: Schema + Store (geen breaking changes)

1. **Schema properties toevoegen** aan `weaviate_schema/collections.py` en `calls.py`
   - 4 collecties, elk 1-2 nieuwe properties
   - `_evolve_collection()` handelt live migratie af

2. **Store functions uitbreiden** met nieuwe parameters (default `""`)
   - `store_video_analysis()`: `+local_filepath`, `+screenshot_dir`
   - `store_session_turn()`: `+local_filepath`
   - `store_call_notes()`: update properties dict
   - `store_content_analysis()`: `+local_filepath`

3. **Tests** voor store functions (bestaande tests blijven werken door defaults)

### Fase 2: Tool-laag (backward-compatible)

4. **`youtube_download.py`**: `target_dir` parameter toevoegen
5. **`video_core.py`**: `local_filepath` + `screenshot_dir` doorgeven aan store
6. **`video.py`**: filepath tracking in `video_analyze` en `video_create_session`
7. **`models/video.py`**: `local_filepath` aan `SessionInfo` toevoegen
8. **Tests** voor tool-laag wijzigingen

### Fase 3: Skills (onafhankelijk van code)

9. **`commands/video.md`**: download naar memory, screenshot locatie update
10. **`commands/video-chat.md`**: lokale video herkenning, frame locatie update
11. **`commands/recall.md`**: lokale assets herkennen en aanbieden
12. **`skills/video-research/SKILL.md`**: documentatie update

### Fase 4: Verificatie

13. **End-to-end test**: YouTube video analyseren → download naar memory → recall → chat sessie starten
14. **Screenshot test**: lokaal bestand → analyse → frame extractie → screenshots in Weaviate
15. **Migratie test**: server starten met bestaande Weaviate data → nieuwe properties verschijnen

---

## 11. Referenties — Betrokken Bestanden

### Schema & Store

| Bestand | Regel(s) | Wijziging |
|---------|----------|-----------|
| `src/video_research_mcp/weaviate_schema/collections.py` | 45-78, 80-100, 155-171 | +`local_filepath`, +`screenshot_dir` properties |
| `src/video_research_mcp/weaviate_schema/calls.py` | 12-39 | +`local_filepath` property |
| `src/video_research_mcp/weaviate_store/video.py` | 15-75 | +params, +properties in dict |
| `src/video_research_mcp/weaviate_store/session.py` | 11-45 | +`local_filepath` param |
| `src/video_research_mcp/weaviate_store/calls.py` | 11-46 | +`local_filepath` in props |
| `src/video_research_mcp/weaviate_store/content.py` | 12-48 | +`local_filepath` param |

### Tools

| Bestand | Regel(s) | Wijziging |
|---------|----------|-----------|
| `src/video_research_mcp/tools/youtube_download.py` | 28-87 | +`target_dir` param |
| `src/video_research_mcp/tools/video_core.py` | 39-106 | +`local_filepath`, +`screenshot_dir` passthrough |
| `src/video_research_mcp/tools/video.py` | 112-195, 249-344 | filepath tracking in tools |
| `src/video_research_mcp/models/video.py` | SessionInfo | +`local_filepath` veld |

### Skills & Commands

| Bestand | Wijziging |
|---------|-----------|
| `commands/video.md` | Download naar memory, screenshot locatie |
| `commands/video-chat.md` | Lokale video herkenning, frame locatie |
| `commands/recall.md` | Lokale assets herkennen bij retrieval |
| `skills/video-research/SKILL.md` | Documentatie nieuwe velden |

### Configuratie

| Bestand | Wijziging |
|---------|-----------|
| `src/video_research_mcp/config.py` | Geen wijzigingen nodig — memory dir is caller-bepaald |

### Geen wijzigingen nodig

| Bestand | Reden |
|---------|-------|
| `src/video_research_mcp/weaviate_client.py` | `_evolve_collection()` handelt migratie automatisch |
| `src/video_research_mcp/tools/knowledge/*.py` | Properties verschijnen automatisch via `serialize()` |
| `src/video_research_mcp/models/knowledge.py` | Generiek `properties: dict` — geen schema-specifieke velden |
| `src/video_research_mcp/cache.py` | File cache ongewijzigd |
| `src/video_research_mcp/context_cache.py` | Context caching ongewijzigd |

---

## 12. Risico's en Aandachtspunten

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Disk space door video downloads | Hoog (honderden MB per video) | `.manifest.json` maakt opruiming eenvoudig; toekomstige `media_cleanup` tool |
| MCP server kent geen project context | Medium | Server slaat pad op dat caller doorgeeft; skills bepalen het pad |
| Bestandspaden breken bij project-verhuizing | Laag | Paden in Weaviate zijn informatief, niet autoritatief — video kan opnieuw worden gedownload |
| Backward-compatibility bestaande Weaviate data | Geen | Nieuwe properties met defaults; `_evolve_collection()` voegt ze toe |
| ffmpeg niet beschikbaar | Laag | Graceful skip met `shutil.which()` check (bestaand patroon) |
| yt-dlp niet beschikbaar | Laag | Bestaande foutafhandeling in `youtube_download.py` |

---

## 13. Toekomstige Uitbreidingen (Buiten Scope)

Deze items zijn **niet** onderdeel van de huidige implementatie maar volgen logisch:

- **`media_cleanup` tool** — disk space management, verwijderen van oude downloads
- **`media_stats` tool** — overzicht van lokale assets (totale grootte, aantal videos, screenshots)
- **Automatische re-download** — als `local_filepath` in Weaviate wijst naar een niet-bestaand bestand, automatisch opnieuw downloaden
- **Thumbnail generatie** — kleine preview-afbeeldingen voor snelle visuele herkenning
- **Cross-project media sharing** — gedeelde media directory buiten project-specifieke memory
