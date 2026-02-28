# Document Research Tool — Design & Implementation Plan

Research and implementation blueprint for `research_document`, a new tool that runs the multi-phase evidence-tiered research pipeline grounded in actual source documents (PDFs, URLs, local files) using Gemini's native document processing.

## 1. Problem Statement

`research_deep` is text-only — it generates research from Gemini's training data + web grounding but cannot analyze caller-provided documents. `content_analyze` handles documents but produces flat single-pass analysis without evidence tiers, cross-referencing, or multi-phase synthesis.

**Gap**: No tool bridges document processing with the structured research pipeline. Users cannot say "analyze these 3 papers and find where their methodologies conflict" or "cross-reference these quarterly reports and surface contradictions."

## 2. Gemini Document Processing Capabilities

Source: [Gemini Document Processing API](https://ai.google.dev/gemini-api/docs/document-processing)

### 2.1 Supported Formats

| Format | Native Vision | Notes |
|--------|--------------|-------|
| PDF | Yes | Charts, tables, diagrams, layouts understood natively |
| TXT/MD/HTML/XML | Text only | Formatting/rendering not interpreted |

PDF is the primary target. Non-PDF text files can be passed as `text/plain` but gain no visual understanding.

### 2.2 Limits

| Constraint | Value |
|------------|-------|
| Max file size | 50 MB |
| Max pages per document | 1,000 |
| Max pages per request | 1,000 (combined across all docs) |
| Token cost per page | ~258 tokens (IMAGE modality) |
| Native text extraction | Free (no token charge for embedded PDF text) |
| Image resolution | Pages scaled to max 3072x3072, small pages to 768x768 |
| File API storage | 48 hours, free |

### 2.3 Upload Mechanisms

**Inline data** — for smaller documents or single-pass analysis:
```python
from google.genai import types

part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
```

**File API** — for larger documents or multi-turn/multi-phase reuse:
```python
uploaded = await client.aio.files.upload(
    file=path, config=types.UploadFileConfig(mime_type="application/pdf")
)
# Poll until ACTIVE
file_info = await client.aio.files.get(name=uploaded.name)
# Reference via URI in any subsequent request
part = types.Part(file_data=types.FileData(file_uri=uploaded.uri))
```

Files uploaded via the File API are stored for 48 hours at no cost and can be referenced by URI across multiple requests — critical for multi-phase pipelines.

### 2.4 Media Resolution (Gemini 3+)

The `media_resolution` parameter controls vision processing granularity per media part:

| Level | Use Case |
|-------|----------|
| low | Fast structure scanning, TOC extraction |
| medium | Balanced analysis, general extraction |
| high | Detailed chart/table/diagram reading |

This enables phase-appropriate resolution: skim in Phase 1, deep-read in Phase 2.

### 2.5 Multi-Document Processing

Multiple PDFs can be included as separate parts in a single request:
```python
parts = [file_part_1, file_part_2, file_part_3, types.Part(text=prompt)]
contents = types.Content(parts=parts)
```

Combined page count must stay under 1,000. This is essential for the cross-reference phase.

## 3. Tool Design

### 3.1 Signature

```python
@research_server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def research_document(
    instruction: Annotated[str, Field(
        description="Research question or analysis instruction to apply to the documents"
    )],
    file_paths: Annotated[list[str] | None, Field(
        description="Local PDF/document file paths"
    )] = None,
    urls: Annotated[list[str] | None, Field(
        description="URLs to PDF documents (downloaded and uploaded to Gemini)"
    )] = None,
    scope: Scope = "moderate",
    thinking_level: ThinkingLevel = "high",
) -> dict:
    """Run multi-phase deep research grounded in source documents.

    Phases: Document Ingestion -> Evidence Extraction -> Cross-Reference -> Synthesis.
    Every claim is labeled with evidence tiers and cited back to source documents.

    Provide at least one of file_paths or urls (both can be provided).

    Args:
        instruction: Research question or what to analyze across documents.
        file_paths: Local paths to PDF or text files.
        urls: URLs to downloadable documents.
        scope: Research depth — "quick", "moderate", "deep", or "comprehensive".
        thinking_level: Gemini thinking depth.

    Returns:
        Dict with document_sources, executive_summary, findings (with citations),
        cross_references, open_questions, methodology_critique.
    """
```

### 3.2 Four-Phase Pipeline

```
Phase 1: Document Ingestion
  ├── Upload all documents via File API (reuse _upload_large_file pattern)
  ├── Download URL-based documents first (httpx)
  ├── Extract structure overview per document (TOC, sections, page count)
  └── Output: list[DocumentMap] + list[file_uri]

Phase 2: Evidence Extraction (per document, parallelizable)
  ├── Extract claims with evidence tiers from each document
  ├── Extract data from tables, charts, figures (native PDF vision)
  ├── Attach page-level citations (e.g., "p.12, Table 3")
  └── Output: list[DocumentFindings]

Phase 3: Cross-Reference Analysis (all documents together)
  ├── All file URIs + extracted findings passed as context
  ├── Identify agreements/consensus across sources
  ├── Surface contradictions and conflicts
  ├── Map evidence chains (claim in doc A supported by data in doc B)
  └── Output: CrossReferenceMap

Phase 4: Synthesis
  ├── Grounded executive summary with source citations
  ├── Evidence-tiered findings with document + page references
  ├── Methodology critique (per-document + overall)
  ├── Open questions and recommendations
  └── Output: DocumentResearchReport
```

### 3.3 Scope Levels

| Scope | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|
| `quick` | Skip (inline parts) | Single-pass extraction | Skip | Brief summary |
| `moderate` | Structure overview | Per-document extraction | Basic cross-ref | Full synthesis |
| `deep` | Detailed mapping | Multi-pass, high resolution | Full cross-ref + evidence chains | Comprehensive report |
| `comprehensive` | All of deep + figure/table inventory | + methodology analysis per doc | + contradiction deep-dive | + recommendations + open questions |

### 3.4 File Handling Strategy

Reuse patterns from `tools/video_file.py`:

```python
LARGE_FILE_THRESHOLD = 20 * 1024 * 1024  # 20 MB (same as video)
DOC_MAX_SIZE = 50 * 1024 * 1024          # 50 MB (Gemini limit)

async def _prepare_document(path: Path) -> tuple[str, str]:
    """Upload document, return (file_uri, content_id).

    Always uses File API for research pipeline (reuse across phases).
    """
    if path.stat().st_size > DOC_MAX_SIZE:
        raise ValueError(f"Document exceeds 50MB Gemini limit: {path.name}")
    mime = "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain"
    content_id = _file_content_hash(path)  # reuse from video_file.py
    uri = await _upload_large_file(path, mime)  # reuse from video_file.py
    return uri, content_id
```

**Key decision**: Always use File API for research documents (even small ones), because multi-phase reuse across 3-4 Gemini calls outweighs the minor upload overhead. This differs from the video/content tools which use inline for <20MB.

For URL sources:
```python
async def _download_document(url: str, tmp_dir: Path) -> Path:
    """Download URL to temp file, return local path."""
    async with httpx.AsyncClient(follow_redirects=True) as http:
        resp = await http.get(url, timeout=60)
        resp.raise_for_status()
    # Write to temp file, return path for _prepare_document()
```

## 4. Data Models

File: `src/video_research_mcp/models/research_document.py`

```python
class DocumentSource(BaseModel):
    """Metadata for a single input document."""
    filename: str
    source_type: str  # "file" | "url"
    original_path: str
    page_count: int = 0
    file_uri: str = ""  # Gemini File API URI

class DocumentMap(BaseModel):
    """Phase 1 output — structure overview of a single document."""
    source: DocumentSource
    title: str = ""
    sections: list[str] = Field(default_factory=list)
    figure_count: int = 0
    table_count: int = 0
    summary: str = ""

class DocumentCitation(BaseModel):
    """A reference back to a specific location in a source document."""
    document: str       # filename or URL
    page: str = ""      # e.g., "p.12" or "pp.12-14"
    section: str = ""   # e.g., "Section 3.2"
    element: str = ""   # e.g., "Table 3", "Figure 7"

class DocumentFinding(BaseModel):
    """Phase 2 output — a single finding extracted from one document."""
    claim: str
    evidence_tier: str = "UNKNOWN"
    citations: list[DocumentCitation] = Field(default_factory=list)
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    reasoning: str = ""
    data_extracted: dict = Field(default_factory=dict)  # tables, charts, figures

class DocumentFindingsContainer(BaseModel):
    """Phase 2 structured output wrapper."""
    document: str
    findings: list[DocumentFinding] = Field(default_factory=list)

class CrossReference(BaseModel):
    """A single cross-reference relationship between documents."""
    relationship: str  # "agrees", "contradicts", "extends", "qualifies"
    claim: str
    sources: list[DocumentCitation] = Field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""

class CrossReferenceMap(BaseModel):
    """Phase 3 output — relationships across all documents."""
    agreements: list[CrossReference] = Field(default_factory=list)
    contradictions: list[CrossReference] = Field(default_factory=list)
    extensions: list[CrossReference] = Field(default_factory=list)
    evidence_chains: list[str] = Field(default_factory=list)

class DocumentResearchReport(BaseModel):
    """Phase 4 final output — complete grounded research report."""
    instruction: str
    scope: str
    document_sources: list[DocumentSource] = Field(default_factory=list)
    executive_summary: str = ""
    findings: list[DocumentFinding] = Field(default_factory=list)
    cross_references: CrossReferenceMap = Field(default_factory=CrossReferenceMap)
    open_questions: list[str] = Field(default_factory=list)
    methodology_critique: str = ""
    recommendations: list[str] = Field(default_factory=list)
```

## 5. Prompt Templates

File: `src/video_research_mcp/prompts/research_document.py`

### 5.1 System Prompt

```
DOCUMENT_RESEARCH_SYSTEM = """
You are a non-sycophantic research analyst specializing in document analysis.
Your job is critical analysis of source documents, not validation of assumptions.

Rules:
- Ground ALL claims in the provided documents — cite page numbers, sections, tables
- State flaws directly without softening language
- Challenge assumptions rather than confirm beliefs
- Label ALL claims with evidence tiers:
  [CONFIRMED] — directly stated with data in the document
  [STRONG INDICATOR] — strongly implied by document evidence
  [INFERENCE] — reasonable conclusion from document context
  [SPECULATION] — extrapolation beyond what documents support
  [UNKNOWN] — documents do not address this
- When extracting data from tables/charts, state the exact values and source location
- Distinguish between what the document claims and what the data shows
"""
```

### 5.2 Phase Prompts

**DOCUMENT_MAP** (Phase 1):
```
Analyze the structure of this document:

RESEARCH INSTRUCTION: {instruction}

Produce:
1. TITLE: Document title or best identifier
2. SECTIONS: List of major sections/chapters
3. FIGURE COUNT: Number of figures, charts, diagrams
4. TABLE COUNT: Number of data tables
5. SUMMARY: 2-3 sentence overview of what this document covers

Focus on structure, not content analysis — that comes in later phases.
```

**DOCUMENT_EVIDENCE** (Phase 2):
```
Extract research findings from this document relevant to the instruction.

INSTRUCTION: {instruction}
DOCUMENT CONTEXT: {document_map}

For EACH finding:
1. State the claim clearly
2. Label its evidence tier
3. Cite the exact location (page, section, table/figure number)
4. List supporting evidence from the document
5. Note any internal contradictions
6. If data is from a table or chart, extract the specific values

Prioritize findings most relevant to the research instruction.
```

**CROSS_REFERENCE** (Phase 3):
```
Cross-reference findings across all provided documents.

INSTRUCTION: {instruction}
FINDINGS PER DOCUMENT:
{all_findings_text}

Produce:
1. AGREEMENTS: Claims that multiple documents support (cite both)
2. CONTRADICTIONS: Where documents disagree (cite specifics)
3. EXTENSIONS: Where one document builds on another's findings
4. EVIDENCE CHAINS: How evidence flows across documents
5. CONFIDENCE MAP: Overall confidence for cross-referenced claims

Be precise about which document says what. Never conflate sources.
```

**DOCUMENT_SYNTHESIS** (Phase 4):
```
Synthesize all document research into a grounded report.

INSTRUCTION: {instruction}
DOCUMENT MAPS: {document_maps}
FINDINGS: {all_findings_text}
CROSS-REFERENCES: {cross_references_text}

Produce:
1. EXECUTIVE SUMMARY: 3-5 sentences grounded in document evidence
2. KEY FINDINGS: Ordered by evidence tier, each with document citations
3. METHODOLOGY CRITIQUE: How each document's methodology affects reliability
4. CROSS-CUTTING PATTERNS: Themes across documents
5. CONTRADICTIONS: Unresolved conflicts and their implications
6. RECOMMENDATIONS: Next steps based on the evidence
7. OPEN QUESTIONS: What the documents leave unanswered

Ground every statement in a specific document. No unsourced claims.
```

## 6. Implementation Architecture

### 6.1 File Layout

```
src/video_research_mcp/
  tools/
    research.py               # existing — add research_document registration
    research_document.py      # NEW — tool function + phase orchestration
    research_document_file.py # NEW — document upload/download helpers
  models/
    research_document.py      # NEW — all models from Section 4
  prompts/
    research_document.py      # NEW — all prompts from Section 5
```

`research_document.py` (tool) stays under 300 lines by extracting file handling to `research_document_file.py`.

### 6.2 Registration

The tool registers on the existing `research_server`:

```python
# tools/research.py — add at bottom
from .research_document import research_document  # noqa: F401 (registers on research_server)
```

Or import in `research_document.py`:
```python
from .research import research_server
```

This keeps the tool in the research sub-server (3 existing + 1 new = 4 tools) without creating a new sub-server.

### 6.3 Phase Execution Flow

```python
async def research_document(...) -> dict:
    try:
        # Validate inputs
        sources = _validate_sources(file_paths, urls)

        # Upload all documents via File API
        prepared = await _prepare_all_documents(sources)
        file_parts = [types.Part(file_data=types.FileData(file_uri=p.file_uri))
                      for p in prepared]

        # Phase 1: Document mapping
        doc_maps = await _phase_document_map(file_parts, instruction, scope)

        if scope == "quick":
            # Skip phases 3-4 for quick scope
            return await _quick_synthesis(file_parts, instruction, doc_maps)

        # Phase 2: Evidence extraction (per document, parallelizable)
        all_findings = await _phase_evidence_extraction(
            file_parts, instruction, doc_maps, scope
        )

        # Phase 3: Cross-reference (skip for single document + moderate scope)
        cross_refs = None
        if len(prepared) > 1 or scope in ("deep", "comprehensive"):
            cross_refs = await _phase_cross_reference(
                file_parts, instruction, all_findings
            )

        # Phase 4: Synthesis
        report = await _phase_synthesis(
            file_parts, instruction, doc_maps, all_findings, cross_refs, scope
        )

        await store_research_finding(report)
        return report

    except Exception as exc:
        return make_tool_error(exc)
```

### 6.4 Parallel Evidence Extraction

Phase 2 can run concurrently across documents:

```python
async def _phase_evidence_extraction(file_parts, instruction, doc_maps, scope):
    """Extract findings from each document in parallel."""
    tasks = [
        _extract_from_document(file_parts[i], instruction, doc_maps[i], scope)
        for i in range(len(file_parts))
    ]
    return await asyncio.gather(*tasks)
```

### 6.5 Weaviate Write-Through

Store to `ResearchFindings` (existing collection) with additional metadata:
- `source_tool: "research_document"`
- Document source paths/URLs in the finding data
- Cross-reference data as part of the finding

No new Weaviate collection needed initially — the existing `ResearchFindings` schema accommodates the enriched output.

## 7. Key Design Decisions

### 7.1 Always Use File API

Unlike `content_analyze` (inline for small files) and `video_analyze` (inline < 20MB), `research_document` always uploads via File API regardless of size. Rationale: 3-4 phases each reference the same documents. Re-uploading inline bytes 4 times for a 15MB PDF wastes bandwidth. File API upload is a one-time cost amortized across all phases.

### 7.2 Download URLs Before Upload

URL documents are downloaded to a temp directory first, then uploaded to Gemini's File API. This avoids the `UrlContext` tool wiring (which doesn't compose well with `response_json_schema` as `content_analyze` discovered) and ensures consistent handling across all document sources.

### 7.3 Scope Controls Phase Depth, Not Phase Count

All scopes run Phase 1 (ingestion) and Phase 2 (extraction). The `quick` scope skips Phases 3-4 and produces a lightweight report. The `comprehensive` scope adds extra extraction passes (methodology analysis, figure/table inventory).

### 7.4 Single Document is Valid

The tool accepts a single document — cross-referencing (Phase 3) is skipped or simplified. This makes it useful for deep single-paper analysis, not just comparative research.

## 8. Use Cases Enabled

| Use Case | Input | Scope | Output |
|----------|-------|-------|--------|
| Paper review | 1 arxiv PDF | moderate | Evidence-tiered findings with page citations |
| Literature review | 3-5 papers | deep | Cross-referenced findings, contradictions, gaps |
| Financial analysis | 4 quarterly PDFs | comprehensive | Trend analysis with table data extraction |
| Due diligence | Contracts + reports | deep | Inconsistency detection, risk flags |
| Competitive analysis | Competitor whitepapers | moderate | Comparative findings, positioning map |
| Regulatory review | Policy documents | comprehensive | Compliance gaps, requirement extraction |

## 9. Cost Considerations

| Factor | Impact |
|--------|--------|
| Native PDF text | Free — no token charge for embedded text |
| Page vision | ~258 tokens/page under IMAGE modality |
| File API storage | Free for 48 hours |
| Pipeline calls | 3-4 Gemini calls per run (same as `research_deep`) |
| `media_resolution` | Low for Phase 1, high for Phase 2 = cost optimization |
| Multi-document | All docs in one request for Phase 3 = single call, not N calls |

**Example**: 3 papers x 20 pages each = 60 pages = ~15,480 vision tokens + free text extraction. At 4 phases, total ~62K vision tokens per research run.

## 10. Implementation Checklist

- [ ] Create `models/research_document.py` — all Pydantic models (Section 4)
- [ ] Create `prompts/research_document.py` — system + 4 phase prompts (Section 5)
- [ ] Create `tools/research_document_file.py` — document upload/download helpers
- [ ] Create `tools/research_document.py` — tool function + phase orchestration
- [ ] Register tool on `research_server` in `tools/research.py`
- [ ] Update `server.py` tool count comment if tracked
- [ ] Add write-through to `weaviate_store.py` (or reuse `store_research_finding`)
- [ ] Write tests: success (single doc), success (multi-doc), scope variations, URL download, upload failure, Gemini failure per phase, file too large
- [ ] Update `CLAUDE.md` — tool table, tool count
- [ ] Update `ARCHITECTURE.md` — research sub-server section
- [ ] Update plugin SKILL.md if tool should be exposed to Claude Code

## 11. Open Questions

1. **Should Phase 2 use the flash model for cost efficiency?** Phase 2 (per-document extraction) is the most token-heavy. Using `gemini-3-flash-preview` for extraction and `gemini-3.1-pro-preview` for synthesis mirrors the `web_search` pattern.

2. **Page limit enforcement**: Should the tool validate combined page count before starting, or let Gemini reject it? Pre-validation is friendlier but requires reading PDF metadata.

3. **Temp file cleanup**: Downloaded URL documents need cleanup. Use `tempfile.TemporaryDirectory` as async context manager, or clean up in a finally block?

4. **Cache integration**: Should results be cached like `video_analyze`? Document content hashes would make good cache keys, but research instructions vary. Consider caching per (content_hash, instruction_hash) pair.

5. **Streaming progress**: The 4-phase pipeline can take 30-60 seconds. Should intermediate results be yielded or logged for progress visibility?
