# Knowledge Conflict Detection — Design & Implementation Plan

Research and implementation blueprint for adding conflict detection to the knowledge store recall pipeline. Surfaces contradictory, outdated, or inconsistent information across stored research findings, video analyses, and content analyses at query time.

## 1. Problem Statement

The knowledge store ingests everything without validation. `weaviate_store.store_*()` writes every tool result unconditionally — no quality gate, no deduplication (except `VideoMetadata`), no consistency check against existing knowledge. When a user runs `/gr:recall` on a topic researched across multiple sessions, sources, or time periods, contradictory claims are returned side-by-side without any indication of conflict.

**Example failure scenario**: A user analyzes three YouTube videos about the same technology. Video A claims "X improves performance by 40%", Video B claims "X has no measurable impact", and a research finding states "X degrades performance under load." All three are stored with high relevance scores. A recall query returns them ranked by vector similarity, not by consistency.

**Gap**: No mechanism exists to detect, surface, or resolve knowledge conflicts at any point in the ingest → storage → recall pipeline.

## 2. Research Findings

### 2.1 Weaviate Has No Native Conflict Detection

Weaviate's "conflict resolution" is about distributed replication (which node wins on write), not semantic contradiction. Vector embeddings measure contextual co-occurrence — "X is safe" and "X is dangerous" have **high** cosine similarity. Neither the QueryAgent nor TransformationAgent provides logical consistency checking.

### 2.2 Academic Literature (arXiv Survey, 2025-2026)

Five recent papers directly inform our design:

| Paper | Key Contribution | Impact on Our Design |
|-------|-----------------|---------------------|
| **DRAGged into Conflicts** (Cattan et al., arXiv:2506.08500, COLM 2025) | Taxonomy of 5 conflict types (No Conflict, Complementary, Freshness, Misinformation, Conflicting Opinions). "Taxonomy-aware prompting" improves response quality by +9 pts (pipeline) to +24 pts (oracle). Gemini 2.5 Flash achieves 65.3% conflict type classification accuracy. | Validates our approach of including conflict type definitions in the Gemini prompt. Adopt their taxonomy as basis for our `conflict_type` classification. |
| **TCR** (Ye et al., arXiv:2601.06842, Jan 2026) | Dual contrastive encoders separate semantic match from factual consistency. +5-18 F1 on conflict detection, +21.4pp knowledge-gap recovery, -29.3pp misleading-context overrides. Only 0.3% parameter overhead. | Confirms that semantic similarity ≠ factual consistency — our prompt must explicitly instruct Gemini to distinguish "same topic" from "same claim." Training custom encoders is out of scope, but the principle is critical. |
| **MADAM-RAG** (Wang et al., arXiv:2504.13079, COLM 2025) | Multi-agent debate over retrieved documents. +11.4% on AmbigDocs, +15.8% on FaithEval (Llama3.3-70B). RAMDocs benchmark shows 32.6 EM — substantial room for improvement. | Multi-agent debate is too expensive for a recall-time check (O(k × rounds)), but the principle of structured argumentation can be encoded in a single-LLM prompt. |
| **Contradiction Detection in RAG** (Gokul et al., arXiv:2504.00180, 2025) | Three contradiction types: self-contradiction, pair contradiction, conditional contradiction. LLM benchmarks: Claude-3 Sonnet + CoT achieves best F1 (0.71), but CoT *hurts* Llama3.3-70B (0.68→0.33). | **Critical finding**: LLMs are mediocre conflict detectors (F1 ~0.71 at best). Our tool must communicate confidence honestly and sensitivity levels must be conservative. CoT may help or hurt depending on the model — we should let Gemini's thinking mode handle this via `thinking_level`. |
| **TruthfulRAG** (arXiv:2511.10375, Nov 2025) | Graph construction from retrieved triples → structured conflict detection → factual-level resolution. | Graph-based approach is more precise but requires triple extraction infrastructure. Relevant for Phase 2 (claim extraction) if we pursue it. |

### 2.3 Established Patterns

Four implementation patterns exist in the literature:

| Pattern | Mechanism | Cost | Fit |
|---------|-----------|------|-----|
| NLI Post-filter | Pairwise cross-encoder classification | Low (no LLM) | Requires pytorch dependency (~500MB) |
| Claim Extraction | Atomic claims stored separately, NLI at recall | Medium | Doubles storage, complex schema |
| Multi-Agent Debate | k agents argue, aggregator synthesizes | High | O(k × rounds × LLM) per query |
| **LLM-as-Judge** | **Single Gemini call analyzes result set for conflicts** | **Medium** | **Fits existing architecture** |

### 2.4 Chosen Approach: Gemini-Powered Conflict Analysis

Use the existing `GeminiClient` to analyze recall results for conflicts in a single structured-output call. This:
- Requires no new dependencies (no pytorch, no NLI models)
- Uses the existing `generate_structured()` pattern
- Runs only at recall time (no ingest slowdown)
- Produces structured output that integrates with existing `KnowledgeSearchResult`

**Academic justification**: DRAGged (2025) shows that taxonomy-aware prompting is within 15 points of oracle performance. TCR (2026) proves factual consistency can be separated from semantic relevance. The Contradiction Detection paper (2025) calibrates our expectations: F1 ~0.71 is realistic for LLM-based detection, so we must surface confidence scores and avoid binary "conflict/no conflict" classifications.

## 3. Tool Design

### 3.1 New Tool: `knowledge_conflicts`

A standalone tool that accepts a topic and searches the knowledge store for conflicting information. Can also accept pre-fetched results to analyze.

```python
@knowledge_server.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True)
)
async def knowledge_conflicts(
    topic: Annotated[str, Field(description="Topic or claim to check for conflicts")],
    collections: Annotated[
        list[KnowledgeCollection] | None,
        Field(description="Collections to search. Default: all.")
    ] = None,
    limit: Annotated[int, Field(description="Max results to analyze", ge=2, le=50)] = 20,
    sensitivity: Annotated[
        ConflictSensitivity,
        Field(description="How aggressively to flag conflicts")
    ] = "balanced",
    thinking_level: ThinkingLevel = "medium",
) -> dict:
    """Detect conflicting or contradictory information stored about a topic.

    Searches the knowledge store for relevant entries, then uses Gemini to
    identify contradictions, inconsistencies, and outdated claims across
    sources. Returns a structured conflict report with evidence citations.

    Args:
        topic: The topic or specific claim to check for conflicts.
        collections: Restrict search to specific collections.
        limit: Number of knowledge entries to retrieve and analyze.
        sensitivity: Detection threshold — 'strict' flags subtle tensions,
            'balanced' flags clear contradictions, 'lenient' flags only
            direct opposites.
        thinking_level: Gemini thinking budget for analysis.

    Returns:
        Dict with conflict report or error via make_tool_error().
    """
```

### 3.2 Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `topic` | `str` | required | What to check for conflicts |
| `collections` | `list[KnowledgeCollection] \| None` | `None` (all) | Scope the search |
| `limit` | `int` (2-50) | 20 | How many entries to analyze |
| `sensitivity` | `ConflictSensitivity` | `"balanced"` | Detection threshold |
| `thinking_level` | `ThinkingLevel` | `"medium"` | Gemini thinking budget |

### 3.3 Types

```python
ConflictSensitivity = Literal["strict", "balanced", "lenient"]
```

### 3.4 Response Model

```python
class ConflictPair(BaseModel):
    """Two knowledge entries that contradict each other."""
    claim_a: str = Field(description="First claim (verbatim or paraphrased)")
    source_a: ConflictSource = Field(description="Source of claim A")
    claim_b: str = Field(description="Contradicting claim (verbatim or paraphrased)")
    source_b: ConflictSource = Field(description="Source of claim B")
    conflict_type: str = Field(description="Category: factual, temporal, methodological, scope")
    severity: str = Field(description="high (direct opposite), medium (tension), low (nuance)")
    explanation: str = Field(description="Why these claims conflict")
    resolution_hint: str = Field(description="Possible explanation for the discrepancy")

class ConflictSource(BaseModel):
    """Reference to a stored knowledge entry."""
    collection: str
    object_id: str
    title: str = ""
    source_tool: str = ""
    created_at: str = ""

class ConflictReport(BaseModel):
    """Complete conflict analysis for a topic."""
    topic: str
    sources_analyzed: int
    collections_searched: list[str]
    conflicts: list[ConflictPair]
    consensus_claims: list[str] = Field(
        description="Claims where all sources agree"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the conflict analysis"
    )
    summary: str = Field(description="Executive summary of findings")
```

### 3.5 Conflict Taxonomy

Based on the DRAGged taxonomy (Cattan et al., 2025) adapted for a knowledge store context:

| Type | Description | Expected Behavior | Example |
|------|-------------|-------------------|---------|
| `factual` | Direct factual contradiction between sources | Flag conflict, cite both sources, note which has stronger evidence | "X costs $10" vs "X costs $50" |
| `temporal` | Information that was true at different times | Flag as temporal, show dates, indicate which is more recent | "X supports Python 2" (2020) vs "X dropped Python 2" (2024) |
| `methodological` | Different measurement approaches yield different results | Present both with methodology context, don't declare a winner | "40% faster (synthetic)" vs "no improvement (production)" |
| `scope` | True in different contexts or at different scales | Clarify the scope of each claim rather than flagging as contradiction | "X is best for small teams" vs "X doesn't scale past 100 users" |
| `opinion` | Genuinely different expert viewpoints | Present all viewpoints without bias, note consensus if any | "Framework A is better" vs "Framework B is better" |

This taxonomy is informed by the CONFLICTS benchmark (DRAGged, 2025) which showed that "Conflicting opinions" is the hardest category for LLMs (36.2% accuracy with Gemini 2.5 Flash), while "Freshness/Misinformation" is relatively easier. Our `sensitivity` parameter addresses this: `strict` mode flags opinion-level tensions, `balanced` focuses on factual/temporal contradictions, `lenient` only flags direct factual opposites.

## 4. Implementation

### 4.1 Pipeline

```
knowledge_conflicts(topic="X")
    │
    ├─ Step 1: Retrieve
    │   knowledge_search(query=topic, search_type="hybrid", limit=limit)
    │   → list[KnowledgeHit]
    │
    ├─ Step 2: Prepare context
    │   Format hits into structured text for Gemini
    │   Include: collection, source_tool, created_at, key properties
    │
    ├─ Step 3: Analyze (Gemini structured output)
    │   GeminiClient.generate_structured(
    │       contents=[context_text],
    │       schema=ConflictReport,
    │       thinking_level=thinking_level,
    │   )
    │
    ├─ Step 4: Enrich
    │   Map Gemini's source references back to actual object_ids
    │   Add collection metadata to ConflictSource objects
    │
    └─ Step 5: Return
        ConflictReport.model_dump()
```

### 4.2 Gemini Prompt

Informed by DRAGged's taxonomy-aware prompting (+9 pts over vanilla) and TCR's semantic-factual separation principle:

```python
CONFLICT_DETECTION_PROMPT = """You are a knowledge conflict detector. Analyze these {count} knowledge store entries about "{topic}" for conflicts and contradictions.

IMPORTANT: Two entries discussing the SAME TOPIC with HIGH SEMANTIC SIMILARITY can still be FACTUALLY INCONSISTENT. Do not confuse topical relevance with factual agreement.

CONFLICT TAXONOMY:
- factual: Direct factual contradiction (e.g., different numbers, opposite claims about the same thing)
- temporal: Information that was true at different times (check dates — newer may supersede older)
- methodological: Different measurement approaches yielding different results (both may be valid in their context)
- scope: True at different scales or in different contexts (not a real contradiction, just different scopes)
- opinion: Genuinely different expert viewpoints on subjective matters

SENSITIVITY LEVEL: {sensitivity}
- strict: Flag any tension, disagreement, or inconsistency — including subtle scope differences and opinion divergence
- balanced: Flag clear contradictions (factual, temporal) and meaningful disagreements. Ignore minor scope/opinion differences
- lenient: Flag only direct factual opposites where one claim MUST be wrong if the other is right

ENTRIES:
{formatted_entries}

ANALYSIS INSTRUCTIONS:
1. For each conflict pair found:
   - Quote or closely paraphrase the specific conflicting claims from each entry
   - Reference entries by their index number [Entry N]
   - Classify using the taxonomy above
   - Rate severity: high (one must be wrong), medium (meaningful tension), low (minor inconsistency)
   - Explain WHY these claims conflict
   - Suggest what might explain the discrepancy (different time periods, contexts, methodologies, or one source being wrong)

2. Identify consensus claims — facts where ALL sources agree

3. Rate your overall confidence in the analysis (0.0-1.0). Lower confidence when:
   - Entries are vague or lack specifics to compare
   - The topic is inherently subjective (opinions domain)
   - You are unsure whether differences are true contradictions or just different framings

PRECISION OVER RECALL: Do NOT manufacture conflicts. If sources discuss different aspects of the same topic without contradicting each other, that is NOT a conflict. It is better to miss a subtle conflict than to flag a false positive."""
```

### 4.3 Entry Formatting

Each knowledge hit is formatted as a numbered entry with its key properties:

```
[Entry 1] Collection: ResearchFindings | Source: research_deep | Date: 2026-02-15
Topic: LLM inference optimization
Claim: "Speculative decoding improves throughput by 2-3x on long sequences"
Evidence tier: CONFIRMED | Confidence: 0.85
---
[Entry 2] Collection: VideoAnalyses | Source: video_analyze | Date: 2026-02-20
Title: "Why Speculative Decoding Fails in Practice"
Summary: "Speculative decoding shows minimal gains (<10%) in production..."
```

Property selection per collection:

| Collection | Key properties for conflict analysis |
|------------|-------------------------------------|
| ResearchFindings | topic, claim, evidence_tier, confidence, supporting, contradicting |
| VideoAnalyses | title, summary, key_points, topics |
| ContentAnalyses | title, summary, key_points, quality_assessment |
| WebSearchResults | query, response |
| SessionTranscripts | video_title, turn_prompt, turn_response |

`VideoMetadata` and `ResearchPlans` are excluded — they contain structural data, not claims.

### 4.4 File Layout

```
src/video_research_mcp/
├── tools/knowledge/
│   ├── conflicts.py          # knowledge_conflicts tool (~120 lines)
│   └── ...
├── models/
│   └── knowledge.py          # + ConflictPair, ConflictSource, ConflictReport
├── prompts/
│   └── conflicts.py          # CONFLICT_DETECTION_PROMPT (~30 lines)
└── types.py                  # + ConflictSensitivity type alias
```

### 4.5 Registration

In `tools/knowledge/__init__.py`, import and register the tool on `knowledge_server`.

## 5. Recall Integration

### 5.1 `/gr:recall` Enhancement

The recall command gains a new argument form:

```
/gr:recall conflicts "topic"     → knowledge_conflicts(topic="topic")
/gr:recall conflicts             → knowledge_conflicts(topic=<last search topic>)
```

When presenting normal recall results, if > 3 results are returned from mixed sources, add a suggestion:

```
💡 Multiple sources found. Run `/gr:recall conflicts "topic"` to check for contradictions.
```

### 5.2 `knowledge_ask` Enhancement

When `knowledge_ask` synthesizes an answer from multiple sources, append a conflict check:

```python
# After generating the answer
if len(sources) >= 3:
    conflict_check = await knowledge_conflicts(
        topic=query, limit=len(sources), sensitivity="balanced"
    )
    if conflict_check.get("conflicts"):
        result["conflict_warning"] = conflict_check
```

This is optional and gated behind a config flag (`KNOWLEDGE_CONFLICT_CHECK=true`).

## 6. Weaviate Storage

Conflict reports are stored in a new `ConflictReports` collection for historical tracking:

```python
CONFLICT_REPORTS_SCHEMA = {
    "name": "ConflictReports",
    "properties": [
        {"name": "topic", "data_type": DataType.TEXT},
        {"name": "summary", "data_type": DataType.TEXT},
        {"name": "conflicts_json", "data_type": DataType.TEXT,
         "skip_vectorization": True},
        {"name": "sources_analyzed", "data_type": DataType.INT,
         "index_range_filters": True},
        {"name": "conflict_count", "data_type": DataType.INT,
         "index_range_filters": True},
        {"name": "sensitivity", "data_type": DataType.TEXT,
         "skip_vectorization": True},
    ]
}
```

This enables queries like "which topics have unresolved conflicts?" via `knowledge_search(collections=["ConflictReports"])`.

## 7. Config

| Variable | Default | Purpose |
|----------|---------|---------|
| `KNOWLEDGE_CONFLICT_CHECK` | `false` | Auto-check conflicts in `knowledge_ask` |
| `CONFLICT_SENSITIVITY` | `balanced` | Default sensitivity for auto-checks |

Added to `ServerConfig` in `config.py`.

## 8. Testing Strategy

### 8.1 Unit Tests (~30 tests)

| Test file | Coverage |
|-----------|----------|
| `test_knowledge_conflicts.py` | Tool registration, parameter validation, sensitivity levels |
| `test_conflict_models.py` | Pydantic model validation, serialization |
| `test_conflict_prompt.py` | Prompt formatting, entry selection per collection |

### 8.2 Key Test Scenarios

```python
@pytest.mark.unit
async def test_conflicts_found():
    """Two entries with opposing claims produce a conflict report."""

@pytest.mark.unit
async def test_no_conflicts():
    """Consistent entries produce empty conflicts list with consensus."""

@pytest.mark.unit
async def test_sensitivity_strict():
    """Strict mode flags subtle tensions that balanced mode ignores."""

@pytest.mark.unit
async def test_empty_knowledge_store():
    """Returns graceful result when no entries match the topic."""

@pytest.mark.unit
async def test_single_collection_filter():
    """collections parameter restricts search scope."""

@pytest.mark.unit
async def test_temporal_conflict_detection():
    """Entries from different dates with contradicting claims are typed 'temporal'."""

@pytest.mark.unit
async def test_weaviate_disabled():
    """Returns make_tool_error when Weaviate is not configured."""
```

### 8.3 Mock Pattern

```python
@pytest.fixture
def mock_search_results():
    """Pre-built KnowledgeHit list with known conflicts for deterministic testing."""
    return [
        KnowledgeHit(
            collection="ResearchFindings",
            object_id="uuid-1",
            score=0.95,
            properties={"claim": "X improves performance by 40%", ...}
        ),
        KnowledgeHit(
            collection="VideoAnalyses",
            object_id="uuid-2",
            score=0.90,
            properties={"summary": "X shows no measurable improvement", ...}
        ),
    ]
```

## 9. Future Extensions

### 9.1 Ingest-Time Pre-Check (Phase 2)

After the recall-time tool is stable, add an optional pre-check during `weaviate_store.store_*()`:

```python
async def store_with_conflict_check(result, topic):
    # Quick search for existing entries on this topic
    existing = await knowledge_search(query=topic, limit=5)
    if existing["total_results"] > 0:
        # Lightweight conflict check (lenient sensitivity, no storage)
        conflicts = await _check_conflicts_lightweight(result, existing)
        if conflicts:
            result["_conflict_warning"] = conflicts
    await store_original(result)
```

This is informational only — it warns but never blocks storage.

### 9.2 Conflict Resolution Workflow (Phase 3)

A `knowledge_resolve` tool that lets users mark conflicts as resolved:

```python
async def knowledge_resolve(
    conflict_id: str,
    resolution: str,  # "a_correct", "b_correct", "both_valid", "context_dependent"
    explanation: str,
) -> dict:
```

### 9.3 NLI Cross-Encoder (Phase 4)

For high-volume deployments, add optional NLI classification as a pre-filter before the Gemini call. This reduces LLM costs by only sending likely-conflicting pairs to Gemini.

## 10. Implementation Checklist

- [ ] Add `ConflictSensitivity` type to `types.py`
- [ ] Add `ConflictPair`, `ConflictSource`, `ConflictReport` to `models/knowledge.py`
- [ ] Create `prompts/conflicts.py` with `CONFLICT_DETECTION_PROMPT`
- [ ] Create `tools/knowledge/conflicts.py` with `knowledge_conflicts` tool
- [ ] Register tool in `tools/knowledge/__init__.py`
- [ ] Add `ConflictReports` to `weaviate_schema.py`
- [ ] Add `store_conflict_report` to `weaviate_store.py`
- [ ] Add config flags to `config.py:ServerConfig`
- [ ] Update `commands/recall.md` with `conflicts` argument
- [ ] Write unit tests (`test_knowledge_conflicts.py`)
- [ ] Update `docs/tutorials/KNOWLEDGE_STORE.md`
- [ ] Update `CLAUDE.md` architecture table (8th sub-server or extended knowledge)
- [ ] Update `CHANGELOG.md`
