# Video Output Contract Hardening + Structured Output Hardening Plan

## Summary
Dit plan vervangt het eerdere hardening-plan en voegt volledige structured-output verbeteringen toe op basis van Gemini docs en repo-grounding.
Resultaat: server-side contract enforcement, strengere schema's, semantische validatie, geen broken links, verplichte artifacts, en documentatie in `docs/` als markdown.

> **Review status**: Plan gevalideerd door 3 parallelle Opus 4.6 agents (architecture alignment, backward compatibility, completeness). Alle kritieke bevindingen zijn verwerkt in deze versie.

## Grounding
1. Huidige toolflow:
`video_analyze` retourneert primair JSON-resultaat; artifact-opbouw gebeurt nu grotendeels in command/agent-laag. Zie [video.py](src/video_research_mcp/tools/video.py), [video_core.py](src/video_research_mcp/tools/video_core.py), [commands/video.md](commands/video.md), [agents/visualizer.md](agents/visualizer.md).

2. Structured output in code nu:
`GeminiClient.generate()` accepteert kwarg `response_schema: dict` (intern vertaald naar `config.response_json_schema` op de `GenerateContentConfig`); `generate_structured()` doet `model_validate_json`. Zie [client.py](src/video_research_mcp/client.py).
Maar custom-schema paden doen vaak alleen `json.loads(...)`. Zie [video_core.py](src/video_research_mcp/tools/video_core.py) en [content.py](src/video_research_mcp/tools/content.py).

3. Gemini-docs (structured output) relevante punten:
- JSON mode + schema: syntactisch valide JSON volgens schema.
- Best practice: semantische validatie in applicatie blijft verplicht.
- Sterke typing (`enum`, `minimum`, `maximum`, `minItems`, `required`, `additionalProperties`) aanbevolen.
- Niet volledige JSON-schema support; schema moet compact blijven.
- Structured outputs + tools is preview-bound aan Gemini 3.1 Pro Preview en Gemini 3 Flash Preview.
Bron: [Gemini Structured Outputs docs](https://ai.google.dev/gemini-api/docs/structured-output?example=recipe).

4. Geobserveerde kwaliteitsproblemen in outputs:
- Oude output heeft broken relatieve links.
- Nieuwe output is consistenter qua links, maar had minder coverage in tijd.
Deze verschillen zijn eerder objectief gemeten door file/link/timestamp inspectie.

5. Bekende codebase constraints:
- `video.py` is momenteel 477 regels — boven de 300-regellimiet. Moet eerst gesplitst worden.
- `content.py:_analyze_url()` heeft al een try/except fallback voor tools+schema incompatibiliteit (regels 139-154).
- `ErrorCategory` is een `str, Enum` — nieuwe members zijn additief en veilig.
- Alle 303 tests zijn unit-level met gemockte Gemini (geen live API calls).

## Besluiten (vast)
1. Focus: `kwaliteit + links`.
2. Contract-layout: self-contained artifact map.
3. Gate-beleid: hard fail bij contractfouten (alleen in strict mode).
4. Strategische notities: altijd verplicht in strict mode.
5. Enforcement: server-side.
6. API-pad: `video_analyze` uitbreiden (na prerequisite refactor).
7. Coverage gate: minimaal `90%`.
8. `strict_contract=true` met `output_schema` custom: niet toegestaan — enforcement via runtime check bovenaan `video_analyze` met `make_tool_error(category="API_INVALID_ARGUMENT")`.
9. Geen backfill van oude outputmappen.
10. Default rapporttaal: Engels, user-configureerbaar via `str` (niet Literal).
11. **Bestaande models (`VideoResult`, `ContentResult`) worden NIET getightend** — aparte strict-modellen voor strict mode.
12. **Alle gedragswijzigingen worden gegated achter `strict_contract=true`** — default pad blijft 100% backward-compatible.
13. **`jsonschema` als optional dependency** — `TypeAdapter` voor interne Pydantic models, `jsonschema` (lazy import) voor user-supplied dict schemas. Zonder installatie: post-validatie overgeslagen met warning.

## Prerequisite: video.py refactor
> **Moet VOOR implementatie gebeuren.** `video.py` is 477 regels, boven de 300-regellimiet.

Split `video.py` in twee modules:
- **`tools/video.py`** (~200 regels): `video_analyze`, `video_batch_analyze`, server-definitie.
- **`tools/video_session.py`** (~200 regels): `video_create_session`, `video_continue_session`, `_continue_cached`, `_continue_uncached`, session-gerelateerde helpers.

Dit creëert headroom voor de strict-mode branching in `video.py`.

## Publieke API en type-wijzigingen
1. Breid `video_analyze` uit in [video.py](src/video_research_mcp/tools/video.py) met:
- `strict_contract: Annotated[bool, Field(description="Enable server-side contract enforcement with quality gates")] = False`
- `report_language: Annotated[str | None, Field(description="Language for generated reports (ISO 639-1, e.g. 'en', 'nl', 'de')")] = None`
- `coverage_min_ratio: Annotated[float, Field(ge=0.01, le=1.0, description="Minimum video coverage ratio for quality gate")] = 0.90`

2. Enforcement bovenaan `video_analyze`:
```python
if strict_contract and output_schema:
    return ToolError(
        error="strict_contract=True cannot be combined with output_schema",
        category=ErrorCategory.API_INVALID_ARGUMENT.value,
        hint="Remove output_schema to use strict contract mode, or disable strict_contract for custom schemas.",
    ).model_dump()
```

> **Opmerking**: `make_tool_error(error: Exception)` accepteert alleen een `Exception` en bepaalt `category`/`hint` automatisch via `categorize_error()`. Voor parameter-validatie fouten met een vooraf bekende category, construeer direct een `ToolError` en call `.model_dump()`. Alternatief: breid `make_tool_error` uit met optionele `category`/`hint` overrides — beslissing bij implementatie.

3. Response-uitbreiding — ALLEEN wanneer `strict_contract=true`:
- `artifact_dir: str`
- `artifacts: dict` met paden (`analysis_md`, `strategy_md`, `concept_map_html`, `screenshot_png`, `frames_dir`)
- `quality: dict` met `status`, `coverage_ratio`, `checks`, en timing-metrics.

**Belangrijk**: Wanneer `strict_contract=false` (default), worden GEEN extra keys toegevoegd aan de response. De response shape is identiek aan de huidige implementatie.

4. Nieuwe modellen (alleen voor strict mode):
- Nieuw bestand [models/video_contract.py](src/video_research_mcp/models/video_contract.py) met:
  `StrictVideoResult`, `StrategyReport`, `ConceptMapNode`, `ConceptMapEdge`, `QualityCheck`, `QualityReport`, `VideoAnalyzeStrictResult`.

> **Niet doen**: `ScreenshotMarker` toevoegen aan `models/video.py`. Screenshot markers zijn een command-layer concept (regex-pattern `[SCREENSHOT:MM:SS:desc]` in `commands/video.md`). Ze horen niet in het server model package.

5. Error model uitbreiden in [errors.py](src/video_research_mcp/errors.py) met:
`DEPENDENCY_MISSING`, `QUALITY_GATE_FAILED`, `ARTIFACT_GENERATION_FAILED`, `SCHEMA_VALIDATION_FAILED`.

## Structured Output Hardening

### 1. Strict-mode models (NIET bestaande models tightenen)
Maak NIEUWE strict-variant modellen — laat `VideoResult` en `ContentResult` ongemoeid:
- `StrictVideoResult` in `models/video_contract.py`: met `Field(min_length=...)`, `min_items`, `Literal` classificatievelden, expliciete `description` op elk veld.
- Gebruik deze ALLEEN in het `strict_contract=true` pad.

**Rationale**: Tightenen van `VideoResult`/`ContentResult` is een HIGH RISK breaking change. Bestaande Gemini responses die nu valide zijn (bijv. lege `title`, korte `key_points` lijst) zouden door `model_validate_json()` geweigerd worden. Alle bestaande tests met `VideoResult(title="X", key_points=["one"])` zouden falen.

### 2. Custom schema-pad hardenen

**Probleem**: `output_schema` is een vrije `dict` (willekeurig JSON Schema). Pydantic `TypeAdapter` werkt alleen met Pydantic types, niet met arbitrary JSON Schema dicts. Dit maakt `TypeAdapter` ongeschikt als universele validator voor user-supplied schemas.

**Beslissing**: twee validatiepaden, afhankelijk van schema-type:

| Schema-type | Validatie | Vereiste |
|------------|-----------|----------|
| Pydantic model (strict-mode interne schemas) | `TypeAdapter(ModelClass).validate_python(parsed)` | Geen extra dependency |
| Vrije `dict` (user `output_schema`) | `jsonschema.validate(parsed, schema)` | `jsonschema>=4.0` als **optional** dependency |

- Introduceer helper in [client.py](src/video_research_mcp/client.py): `generate_json_validated(...)`.
- Deze helper doet:
  1. Gemini call met `response_schema` kwarg (let op: dit is de Python kwarg, niet het interne config-attribuut `response_json_schema`)
  2. `json.loads(raw)`
  3. Validatie:
     - Als `schema` een Pydantic model is: `TypeAdapter(schema).validate_python(parsed)`
     - Als `schema` een `dict` is: lazy `import jsonschema; jsonschema.validate(parsed, schema)`.
       Bij `ImportError`: log warning ("jsonschema not installed, skipping post-validation"), return parsed ongevalideerd.
  4. Uniforme error-mapping naar `SCHEMA_VALIDATION_FAILED`
- **`strict: bool` parameter** bepaalt fail-gedrag:
  - `strict=False` (default): log warning bij validatiefout, return parsed data (warn-only).
  - `strict=True` (alleen in strict-mode pipeline): raise/return error bij validatiefout.
- Vervang directe `json.loads` in [video_core.py](src/video_research_mcp/tools/video_core.py) en [content.py](src/video_research_mcp/tools/content.py) door deze helper met `strict=False`.

**Dependency-wijziging in `pyproject.toml`**:
```toml
[project.optional-dependencies]
strict = ["jsonschema>=4.0"]
agents = ["weaviate-agents>=1.2.0"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "ruff>=0.6", "jsonschema>=4.0"]
```
`jsonschema` is alleen nodig voor post-validatie van user-supplied dict schemas. Zonder `jsonschema` werkt alles — validatie wordt overgeslagen met een warning.

### 3. Semantische validatie-laag (na schema-parse)
- Nieuwe module [src/video_research_mcp/validation.py](src/video_research_mcp/validation.py) (package-root, NIET in `tools/`).
- Valideer business rules:
  - timestamp formaat en monotoniciteit
  - minimum key-point kwaliteit
  - concept-edge integriteit
  - coverage vs video duration
  - **zero-duration guard**: als `duration_seconds == 0` (live stream), skip coverage check of gebruik fallback.
- Fail met `QUALITY_GATE_FAILED` indien `strict_contract=true`. Warn-only bij default.

### 4. Model-compat guard voor structured outputs + tools
- In [client.py](src/video_research_mcp/client.py) (cross-cutting concern, NIET in content.py):
  - Als `tools` + `response_schema` beide worden meegegeven aan `generate()`, check of het actieve model compatible is (Gemini 3.1 Pro Preview / Gemini 3 Flash Preview).
  - **Mode-afhankelijk gedrag**:
    - **Strict mode** (`strict=True` meegegeven als context): hard fail met `SCHEMA_VALIDATION_FAILED` error. Caller verwacht gegarandeerd structured output; stilzwijgend strippen breekt het contract.
    - **Default mode**: log warning en strip `response_schema` (graceful degradation). Dit is het bestaande gedrag van `content.py:_analyze_url()` (regels 139-154), maar nu centraal in de client.
  - Implementatie: voeg optionele `strict_schema: bool = False` parameter toe aan `generate()`. Bij `strict_schema=True` + incompatibel model: raise `ValueError("Model {model} does not support tools + structured output")` i.p.v. strippen.
- **Opmerking**: `content.py:_analyze_url()` behoudt zijn bestaande try/except fallback als extra vangnet. De client-level guard voorkomt dat andere tools dezelfde fout maken.

### 5. Schema-complexity guard
- Voeg util toe in [src/video_research_mcp/schema_guard.py](src/video_research_mcp/schema_guard.py) (package-root, NIET in `tools/`).
- Rule-set:
  - max depth (default: 5)
  - max property count (default: 50)
  - max enum size (default: 20)
- Error hint verwijst naar vereenvoudigen van schema (conform docs limitation).
- Geschatte omvang: ~60 regels.

## Contract-pipeline implementatie

### Module-plaatsing
**Niet in `tools/`** — de contract pipeline is business logic, geen MCP tool registratie. Elk bestand in `tools/` registreert `@server.tool()` decorators of is een directe helper daarvoor.

Pipeline als package:
```
src/video_research_mcp/contract/
  __init__.py              # re-exporteert run_strict_pipeline()
  pipeline.py              # orchestratie (~120 regels)
  render.py                # markdown/HTML artifact generatie (~100 regels)
  quality.py               # quality gates, coverage berekening (~80 regels)
```

### Pipeline stages bij `strict_contract=true`
1. **Analyse** (structured via `StrictVideoResult`) — hergebruik `analyze_video()` uit `video_core.py`
2. **Strategie-rapport** (structured via `StrategyReport`) — aparte Gemini call
3. **Concept-map data** (structured via `ConceptMapNode`/`ConceptMapEdge`) — aparte Gemini call
4. **Artifact rendering** (`analysis.md`, `strategy.md`, `concept-map.html`, `screenshot.png`, `frames/` voor lokale files)
5. **Quality gates** — coverage, link-integriteit, completeness
6. **Verrijkte response**

> Stages 2 en 3 zijn onafhankelijk van elkaar en kunnen parallel uitgevoerd worden met `asyncio.gather()`.

### Screenshot en frames: technische keuze

| Artifact | Bron | Methode | Dependency |
|----------|------|---------|------------|
| `screenshot.png` (YouTube) | YouTube thumbnail | `google-api-python-client` via `thumbnails.high.url` uit video metadata | Bestaande dependency |
| `screenshot.png` (lokaal bestand) | Key frame uit video | `ffmpeg -ss <midpoint> -vframes 1` | ffmpeg (system-level, al gebruikt in `commands/video.md`) |
| `frames/` (lokaal bestand) | Frame extractie op timestamps | `ffmpeg -ss <timestamp> -vframes 1` per timestamp | ffmpeg (system-level) |
| `concept-map.html` | Concept-map data | Template rendering in `contract/render.py` | Geen extra dependency (inline HTML/SVG) |

**ffmpeg guard**: check `shutil.which("ffmpeg")` bij pipeline start. Bij lokale bestanden zonder ffmpeg: return `make_tool_error()` met `DEPENDENCY_MISSING` category en hint `"Install ffmpeg for local video artifact generation"`. YouTube-analyse heeft GEEN ffmpeg nodig (thumbnail via API).

**Beslissing**: geen Playwright/Pillow dependency. Screenshots zijn video frames (ffmpeg) of thumbnails (YouTube API). De concept-map HTML is een zelfstandig bestand, geen browser-rendered screenshot.

### Output locatie en veiligheid
- Base directory: `<cwd>/output/<slug>` (of configureerbaar via env var `VIDEO_OUTPUT_DIR`).
- **Slug sanitization** (VERPLICHT):
  ```python
  def sanitize_slug(title: str) -> str:
      """Sanitize a video title into a safe filesystem slug.

      Raises:
          ValueError: If the resulting slug is empty or contains path traversal.
      """
      slug = re.sub(r'[^a-z0-9-]', '', title.lower().replace(' ', '-'))
      slug = re.sub(r'-+', '-', slug).strip('-')[:50]
      if not slug:
          raise ValueError(f"Cannot derive safe slug from title: {title!r}")
      if Path(slug).name != slug:
          raise ValueError(f"Slug contains path traversal: {slug!r}")
      return slug
  ```
  Strip alle `..`, `/`, speciale tekens. Gebruik expliciete `raise ValueError` — GEEN `assert` (kan uitgeschakeld worden met `python -O`). Reject als slug leeg is of `Path(slug).name != slug`.
- **Atomaire schrijfstrategie**: schrijf alle artifacts naar een temp directory (`<output>/.tmp-<uuid>`), pas bij volledige pipeline success atomair hernoemen naar de finale locatie. Bij failure: cleanup temp directory.
- **Concurrency**: als de artifact directory al bestaat, append een korte UUID suffix (`<slug>-a1b2c3`). Geen file-locking nodig — elk request krijgt een uniek pad.

### Backward compatibility
`video_analyze` zonder `strict_contract=true` blijft 100% backward-compatible — zelfde code-pad, zelfde response shape, geen extra keys.

## Interactie met bestaande features

### video_batch_analyze
`strict_contract` parameter wordt **genegeerd** in `video_batch_analyze`. Batch results gebruiken de bestaande pipeline. Rationale: batch draait met semaphore van 3 concurrent calls; de strict pipeline maakt 3+ Gemini calls per video, wat 9+ gelijktijdige Gemini requests betekent — te duur en te traag.

### Sessions (video_create_session / video_continue_session)
Strict-mode artifacts en sessions zijn **onafhankelijk**. `SessionInfo` krijgt geen `artifact_dir` veld in deze fase. Toekomstige integratie (bijv. strict artifacts koppelen aan sessie) is een apart plan.

### Weaviate write-through
De base video analyse wordt nog steeds gepersisteerd naar Weaviate via het bestaande `store_video_analysis()` pad. Strict-mode artifacts (strategy, concept map, quality report) worden **alleen als lokale bestanden** opgeslagen. Nieuwe Weaviate collections voor strict-mode data zijn out of scope voor deze fase.

### Context cache
De strict pipeline hergebruikt de bestaande context-cache voor de eerste analyse-stap. De strategie- en concept-map stages krijgen eigen cache keys: `{content_id}_strict_strategy`, `{content_id}_strict_concept_map`. Bij retry wordt alleen de gefailde stage opnieuw uitgevoerd.

## Performance budget
| Stage | Verwachte duur | Gemini calls | Tokens (geschat) |
|-------|---------------|--------------|-------------------|
| Analyse | 30-60s | 1 | 10-50K input, 2-5K output |
| Strategie | 15-30s | 1 | 5-10K input, 2-3K output |
| Concept-map | 15-30s | 1 | 5-10K input, 1-2K output |
| Rendering | 1-2s | 0 | n.v.t. |
| Quality gates | <1s | 0 | n.v.t. |
| **Totaal** | **~60-120s** | **3** | **~20-70K input** |

- Stages 2+3 parallel: besparing ~15-30s.
- `thinking_level` voor stages 2+3: verlaag naar `"medium"` (hoofdanalyse al beschikbaar als context).
- MCP progress notifications via FastMCP (indien ondersteund): "Stage 2/5: Generating strategy report..."
- Per-stage timeout: 90 seconden. Pipeline totaal timeout: 300 seconden.

## Command/agent alignment
1. **Fase 1**: `commands/video.md` blijft ONGEWIJZIGD. Strict mode is opt-in via directe tool-aanroep, niet via het command.
2. **Fase 2** (apart): Nadat strict mode stabiel is bewezen, maak een nieuw command `commands/video-strict.md` of voeg een flag toe aan het bestaande command. Dit is een **bewuste, gedocumenteerde** gedragswijziging, geen stille migratie.
3. Houd [agents/comment-analyst.md](agents/comment-analyst.md) als optionele enrichment, maar laat schrijven naar `analysis.md` in artifact-dir.
4. `visualizer` wordt optioneel voor extra views; niet meer required voor contract-core.

**Rationale**: Het wijzigen van `commands/video.md` in Fase 1 zou ALLE `/gr:video` gebruikers raken — response shape verandert, output directory verandert, de command-layer parsing verwacht andere keys. Dit is een HIGH RISK breaking change die apart gerold moet worden.

## Tests en acceptatie
1. Unit tests (alle gemockt, `asyncio_mode=auto`):
- `tests/test_schema_guard.py` — schema complexity guards
- `tests/test_validation.py` — semantische validatie module
- `tests/test_video_contract.py` — contract pipeline (per stage gemockt)
- `tests/test_video_contract_artifacts.py` — filesystem assertions: artifact bestanden bestaan, links kloppen, HTML parsebaar, directory structuur correct (schrijft naar `tmp_path`)

2. Uitgebreide tool tests (unit-level, gemockt):
- Uitbreiding [tests/test_video_tools.py](tests/test_video_tools.py):
  - strict success (YouTube + local)
  - strict fail op broken links/missing files
  - strict fail op coverage < 0.90
  - strict + custom schema => `API_INVALID_ARGUMENT` error
  - backward compatibility: `strict_contract=false` geeft exact dezelfde response shape als nu
  - `coverage_min_ratio` buiten bounds (0.0, 1.5) => Pydantic validation error
  - zero-duration video (live stream) => coverage check skipped
  - concurrent strict calls voor dezelfde video => unieke artifact dirs

3. Acceptance criteria:
- Geen broken lokale links in `analysis.md` + `strategy.md`.
- Verplichte artifact set altijd aanwezig bij success.
- Coverage ratio >= ingestelde threshold.
- Custom-schema paden loggen warnings bij validatiefouten (warn-only).
- Semantische validator rejectt ongeldige maar schema-compliant output (alleen in strict mode).
- Default pad (`strict_contract=false`) produceert identieke output als huidige implementatie.
- Partial artifact cleanup bij pipeline failure — geen half-geschreven directories.

## Rollout
1. **Fase 1**: Prerequisite refactor — split `video.py` in `video.py` + `video_session.py`.
2. **Fase 2**: Introduceer strict mode + structured-output hardening achter opt-in (`strict_contract=false` default).
3. **Fase 3**: Documentatie updates (`ARCHITECTURE.md`, `CLAUDE.md`, tutorials).
4. **Fase 4**: Handmatige smoke in nieuwe Claude sessie.
5. **Fase 5** (apart plan): Migreer `/gr:video` command naar strict mode (nieuw command of flag). Dit is een aparte, gedocumenteerde breaking change met versie-bump.

## Documentatie-output naar docs-folder
1. Doelbestand: [docs/plans/VIDEO_OUTPUT_CONTRACT_HARDENING.md](docs/plans/VIDEO_OUTPUT_CONTRACT_HARDENING.md)

2. Bestand bevat exact:
- Dit volledige plan (inclusief Grounding, API, tests, assumptions).
- Extra sectie "Source Grounding" met repo-bestandspaden en Gemini-docs link + kernclaims.
- Sectie "Decision Log" met alle vastgezette keuzes.

3. Updates in andere docs:
- **`CLAUDE.md`**: update tool parameter lijst voor `video_analyze`, voeg nieuwe error categories toe, voeg `VIDEO_OUTPUT_DIR` env var toe.
- **`docs/ARCHITECTURE.md`**: voeg sectie "Related Plans" toe (bestaat nog niet) met verwijzing naar dit document.
- **`ROADMAP.md`**: link naar dit plan indien van toepassing.

## Assumpties en defaults
1. `strict_contract` is opt-in default `False`.
2. `/gr:video` wordt NIET gewijzigd in Fase 1 — strict mode is opt-in via directe tool-aanroep.
3. Rapporttaal default `"en"`, type `str` (niet `Literal`) voor uitbreidbaarheid.
4. Oude outputmappen worden niet automatisch gemigreerd.
5. Hard fail policy geldt alleen in strict mode.
6. Bestaande `VideoResult`/`ContentResult` models worden niet aangeraakt.
7. `jsonschema>=4.0` als **optional** dependency (`pip install video-research-mcp[strict]`). Pydantic `TypeAdapter` voor interne strict-mode models; `jsonschema` voor user-supplied dict schemas. Zonder `jsonschema` geïnstalleerd werkt alles — post-validatie wordt overgeslagen met warning.
8. `video_batch_analyze` en sessions zijn onafhankelijk van strict mode.
9. Strict-mode artifacts worden niet naar Weaviate geschreven (alleen lokale bestanden).
10. Per-stage caching voorkomt onnodige Gemini calls bij retry.

## Nieuwe module-inventaris
| Module | Locatie | Regels (schatting) | Doel |
|--------|---------|-------------------|------|
| `video_session.py` | `tools/` | ~200 | Session tools (split uit video.py) |
| `video_contract/__init__.py` | `contract/` | ~10 | Re-export `run_strict_pipeline` |
| `video_contract/pipeline.py` | `contract/` | ~120 | Pipeline orchestratie |
| `video_contract/render.py` | `contract/` | ~100 | Artifact rendering |
| `video_contract/quality.py` | `contract/` | ~80 | Quality gates |
| `validation.py` | package root | ~80 | Semantische validatie |
| `schema_guard.py` | package root | ~60 | Schema complexity guard |
| `models/video_contract.py` | `models/` | ~90 | Strict-mode Pydantic models |

**Totaal nieuwe code**: ~740 regels verdeeld over 8 bestanden. Geen bestand boven de 200 regels.

## Risk register
| Risk | Ernst | Mitigatie |
|------|-------|----------|
| Slug path traversal | CRITICAL | `sanitize_slug()` met expliciete `raise ValueError` (geen `assert`) |
| Partial artifacts bij failure | CRITICAL | Atomaire temp-dir + rename strategie |
| Breaking change VideoResult | HIGH | Aparte strict models, bestaande ongewijzigd |
| Breaking change /gr:video | HIGH | Command ongewijzigd in Fase 1 |
| Race conditions concurrent calls | MEDIUM | UUID suffix bij directory collision |
| video.py boven 300-regellimiet | MEDIUM | Prerequisite refactor naar video_session.py |
| Pipeline latency (60-120s) | MEDIUM | Parallel stages 2+3, per-stage caching |
| jsonschema dependency bloat | LOW | Optional dependency (`[strict]` extra), lazy import, graceful degradation |
| Schema stripping breekt contract | MEDIUM | Mode-afhankelijk: strict = hard fail, default = warn + strip |
| Screenshot dependency onduidelijk | LOW | YouTube: thumbnail via API; lokaal: ffmpeg; geen Playwright/Pillow |
| `make_tool_error` API mismatch | LOW | Gebruik `ToolError(...).model_dump()` direct, of breid `make_tool_error` uit |

## Source Grounding

### Repository files referenced
- `src/video_research_mcp/tools/video.py` — main video_analyze tool (split into video.py + video_session.py)
- `src/video_research_mcp/tools/video_core.py` — shared analysis pipeline
- `src/video_research_mcp/client.py` — GeminiClient singleton (extended with generate_json_validated)
- `src/video_research_mcp/errors.py` — ErrorCategory enum (extended with 4 new members)
- `src/video_research_mcp/models/video.py` — existing VideoResult model (NOT modified)

### External documentation
- [Gemini Structured Outputs docs](https://ai.google.dev/gemini-api/docs/structured-output) — JSON mode + schema support, semantic validation requirement, compact schema best practice

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Separate strict models (not tightening existing) | Avoid breaking 300+ existing tests and all default-mode callers |
| 2 | `jsonschema` as optional dependency | Zero-cost for default mode; `TypeAdapter` covers Pydantic schemas |
| 3 | Lazy import of contract package | Keeps startup fast; contract code only loaded when strict_contract=True |
| 4 | Atomic temp-dir + rename for artifacts | Prevents half-written artifact directories on pipeline failure |
| 5 | Slug sanitization with explicit ValueError | Security-critical: prevents path traversal, no assert (can be disabled with -O) |
| 6 | video_batch_analyze ignores strict_contract | 3+ Gemini calls per video × 3 concurrency = 9+ parallel calls — too expensive |
| 7 | Commands/agents unchanged in this phase | HIGH RISK breaking change; separate rollout after strict mode is proven stable |
| 8 | `ToolError().model_dump()` for known categories | `make_tool_error()` only accepts Exception; direct ToolError is cleaner for param validation |
| 9 | Coverage check skipped for duration=0 | Live streams have no known duration; would always fail |
| 10 | Screenshots deferred | YouTube thumbnails via API, local via ffmpeg — implemented separately per P2 feedback |
