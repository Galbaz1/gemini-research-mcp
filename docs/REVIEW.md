# Documentation Cross-Review

**Date**: 2026-02-27
**Reviewer**: code-reviewer (Claude Opus 4.6)
**Scope**: Consistency, accuracy, and completeness across all generated docs

**Files reviewed:**
- `docs/ARCHITECTURE.md`
- `docs/DIAGRAMS.md`
- `docs/AUDIT.md`
- `docs/tutorials/GETTING_STARTED.md`
- `docs/tutorials/ADDING_A_TOOL.md`
- `docs/tutorials/WRITING_TESTS.md`
- `docs/tutorials/KNOWLEDGE_STORE.md`

---

## 1. Tool Count Inconsistency

The audit (AUDIT.md) identified the actual tool count as **18** (4+2+3+2+1+2+4). The generated docs are inconsistent:

| Document | Claim | Correct? |
|----------|-------|----------|
| ARCHITECTURE.md title (line 11) | "Tool Reference (17 tools)" | **WRONG -- should be 18** |
| ARCHITECTURE.md line 25 | "exposes 17 tools" | **WRONG -- should be 18** |
| ARCHITECTURE.md line 85 | "the total is 17" | **WRONG -- should be 18** |
| ARCHITECTURE.md line 323 | "## 5. Tool Reference (17 tools)" | **WRONG -- should be 18** |
| DIAGRAMS.md | Lists all 18 tools correctly in diagram 1 | CORRECT |
| GETTING_STARTED.md line 108 | "The 15 tools will appear" | **WRONG -- should be 18** |
| ADDING_A_TOOL.md overview tree | 4+2+3+2+1+2+4 = 18 (implicit) | CORRECT (counts per server are right) |
| KNOWLEDGE_STORE.md | No total count claim | N/A |
| WRITING_TESTS.md line 13 | "72+ tests across 17 test files" | **WRONG -- should be "228 tests"** |

The architecture guide adopted the old "17 tools" number despite the audit report flagging this. The getting started tutorial says "15 tools" which is even more stale. The writing tests tutorial says "72+" which is far below the actual 228.

**Action required**: Fix all tool count references to 18, test count references to 228.

---

## 2. Terminology Consistency

### Consistent terms (good)

- "FastMCP" -- used consistently across all docs
- "sub-server" -- consistent naming for mounted servers
- "write-through" -- consistent pattern name for Weaviate storage
- "structured output" -- consistent for Gemini JSON schema output
- "thinking level" -- consistent naming across all docs
- "content_id" -- consistent cache key terminology
- Tool names -- identical across all docs (no spelling variants)

### Inconsistent terms

| Term | ARCHITECTURE.md | Tutorials | Notes |
|------|----------------|-----------|-------|
| FastMCP version | "FastMCP 3.0.2" (line 25) | Not mentioned | AUDIT.md flagged pyproject.toml says `>=2.0`. Architecture guide should drop the specific version or say "FastMCP 3.x" |
| Session persistence | "optional SQLite backing" (line 555) | "WAL mode" (KNOWLEDGE_STORE.md, indirectly) | Architecture guide is more precise, tutorials mention it less |
| Model presets | Full table with model IDs | Shown as CLI examples | Consistent enough |

### Naming alignment with code

All tool names, model names, config field names, and collection names in the docs match the actual source code. No invented or misspelled identifiers found.

---

## 3. Cross-Reference Accuracy

### Tutorial cross-references

| From | To | Link Works? | Content Matches? |
|------|----|:-----------:|:----------------:|
| GETTING_STARTED.md -> ADDING_A_TOOL.md | `./ADDING_A_TOOL.md` | PASS | PASS |
| GETTING_STARTED.md -> WRITING_TESTS.md | `./WRITING_TESTS.md` | PASS | PASS |
| GETTING_STARTED.md -> KNOWLEDGE_STORE.md | `./KNOWLEDGE_STORE.md` | PASS | PASS |
| GETTING_STARTED.md -> ARCHITECTURE.md | `../ARCHITECTURE.md` | PASS | PASS |
| ADDING_A_TOOL.md -> ARCHITECTURE.md | `../ARCHITECTURE.md` | PASS | PASS |
| ADDING_A_TOOL.md -> WRITING_TESTS.md | `./WRITING_TESTS.md` | PASS | PASS |
| ADDING_A_TOOL.md -> KNOWLEDGE_STORE.md | `./KNOWLEDGE_STORE.md` | PASS | PASS |
| WRITING_TESTS.md -> ADDING_A_TOOL.md | `./ADDING_A_TOOL.md` | PASS | PASS |
| WRITING_TESTS.md -> KNOWLEDGE_STORE.md | `./KNOWLEDGE_STORE.md` | PASS | PASS |
| KNOWLEDGE_STORE.md -> GETTING_STARTED.md | `./GETTING_STARTED.md` | PASS | PASS |
| KNOWLEDGE_STORE.md -> ADDING_A_TOOL.md | `./ADDING_A_TOOL.md` | PASS | PASS |
| KNOWLEDGE_STORE.md -> WRITING_TESTS.md | `./WRITING_TESTS.md` | PASS | PASS |
| KNOWLEDGE_STORE.md -> ARCHITECTURE.md | `../ARCHITECTURE.md` | PASS | PASS |

All relative links are correct. Cross-references form a complete web -- every tutorial links to every other tutorial and to the architecture guide.

### Source file references

| Reference | In Doc | File Exists? |
|-----------|--------|:------------:|
| `src/video_research_mcp/tools/content.py` | ADDING_A_TOOL.md | PASS |
| `src/video_research_mcp/client.py` | ADDING_A_TOOL.md | PASS |
| `tests/conftest.py` | WRITING_TESTS.md | PASS |
| `tests/test_video_tools.py` | WRITING_TESTS.md | PASS |
| `tests/test_knowledge_tools.py` | WRITING_TESTS.md | PASS |
| `src/video_research_mcp/weaviate_schema.py` | KNOWLEDGE_STORE.md | PASS |
| `src/video_research_mcp/weaviate_store.py` | KNOWLEDGE_STORE.md | PASS |
| `src/video_research_mcp/weaviate_client.py` | KNOWLEDGE_STORE.md | PASS |
| `src/video_research_mcp/tools/knowledge.py` | KNOWLEDGE_STORE.md | PASS |

All source file references point to actual files.

---

## 4. Diagram vs Architecture Guide Consistency

### Diagram 1: Server Mounting Hierarchy

- Lists 7 sub-servers: MATCHES architecture guide section 2
- Lists 18 tools under correct sub-servers: MATCHES actual code
- Shows lifespan hook with WeaviateClient.aclose() + GeminiClient.close_all(): MATCHES server.py

### Diagram 2: GeminiClient Request Flow

- Shows cache check -> schema branch -> config resolution -> retry -> API -> strip thinking -> validate -> cache write -> Weaviate write-through: MATCHES architecture guide section 3
- Retry patterns listed as "429, 503, 500" in diagram: code actually matches on `429`, `quota`, `resource_exhausted`, `timeout`, `503`, `service unavailable`. **Minor: diagram says "500" but code has no "500" pattern**. Code matches `503` and `service unavailable`, not generic 500.

### Diagram 3: Session Lifecycle

- Shows eviction, cap check, allocation, continue turn flow: MATCHES architecture guide section 8
- Shows SQLite WAL persistence as conditional: MATCHES code
- Shows history trim to `session_max_turns * 2`: MATCHES code
- Shows Weaviate store_session_turn: MATCHES code

### Diagram 4: Weaviate Data Flow

- Lists 8 producer tools: MATCHES `weaviate_store.py` (8 store functions)
- Lists 11 collections with key properties: MATCHES `weaviate_schema/`
- Lists 4 knowledge query tools: MATCHES `tools/knowledge.py`
- Shows WeaviateClient singleton as intermediary: MATCHES architecture

**Overall**: Diagrams are accurate and consistent with both the architecture guide and source code, with one minor issue in Diagram 2 (500 vs actual retry patterns).

---

## 5. Audit Findings Coverage

Checking whether the audit's critical findings are addressed in the other docs:

| Audit Finding | Addressed? | Where |
|--------------|:----------:|-------|
| Tool count is 18 not 17 | **NO** -- architecture guide still says 17 | Needs fix |
| "All 11 tools" stale reference | N/A (only in CLAUDE.md) | CLAUDE.md fix needed |
| Test count is 228 not 72 | **NO** -- WRITING_TESTS.md says "72+" | Needs fix |
| Missing tree entries (retry.py, persistence.py, video_file.py) | **YES** | ARCHITECTURE.md source layout includes all three |
| Undocumented write-through pattern | **YES** | ARCHITECTURE.md section 7, KNOWLEDGE_STORE.md |
| WeaviateClient missing from singletons | **YES** | ARCHITECTURE.md section 6 lists all 5 singletons |
| Session store SQLite description | **YES** | ARCHITECTURE.md section 8 describes SQLite persistence |
| FastMCP version mismatch | **NO** -- still says "FastMCP 3.0.2" | ARCHITECTURE.md line 25 |

---

## 6. Code Example Accuracy

### ADDING_A_TOOL.md examples

- `content_compare` example: follows all conventions correctly (ToolAnnotations, Annotated params, docstring, make_tool_error). **Valid**.
- New sub-server example: correct FastMCP instantiation, import pattern, mount in server.py. **Valid**.
- Test example: uses `mock_gemini_client` fixture correctly, tests success + error paths. **Valid**.

### WRITING_TESTS.md examples

- `mock_gemini_client` fixture usage: matches actual `conftest.py`. **Valid**.
- `clean_config` fixture: matches actual code. **Valid**.
- `mock_weaviate_client` fixture: matches actual code. **Valid**.
- Video analyze test example: matches patterns in actual `test_video_tools.py`. **Valid**.
- Knowledge search test example: uses correct lazy-import pattern and fixture combo. **Valid**.

### GETTING_STARTED.md examples

- Installation commands: correct (`uv venv`, `uv pip install -e ".[dev]"`). **Valid**.
- MCP config JSON: correct structure for Claude Code `.mcp.json`. **Valid**.
- Env vars: all match `config.py:from_env()`. **Valid**.

### KNOWLEDGE_STORE.md examples

- Docker command: standard Weaviate Docker setup. **Valid**.
- Collection definitions: match `weaviate_schema.py` exactly (property names, types, vectorization). **Valid**.
- Store function pattern: matches actual `weaviate_store.py`. **Valid**.
- New collection example: follows actual `CollectionDef` pattern. **Valid**.

---

## 7. Issues Summary

### Must Fix (3 issues)

1. **ARCHITECTURE.md**: Change "17 tools" to "18 tools" in 4 locations (lines 11, 25, 85, 323)
2. **GETTING_STARTED.md line 108**: Change "15 tools" to "18 tools"
3. **WRITING_TESTS.md line 13**: Change "72+ tests" to "228 tests"

### Should Fix (2 issues)

4. **ARCHITECTURE.md line 25**: "FastMCP 3.0.2" should be "FastMCP 3.x" or just "FastMCP" (pyproject.toml says `>=2.0`)
5. **DIAGRAMS.md Diagram 2**: Retry patterns mention "500" but code does not match on generic 500 (matches 503, timeout, quota patterns)

### Nice to Have (1 issue)

6. **ARCHITECTURE.md/DIAGRAMS.md**: No cross-references to each other. Architecture guide could link to "See DIAGRAMS.md for visual representations" and diagrams could link back to "See ARCHITECTURE.md for detailed descriptions".

---

## 8. Overall Assessment

The documentation set is **comprehensive and well-structured**. The architecture guide covers every major system in detail, the tutorials build on each other logically, and the diagrams accurately visualize the architecture. Cross-references between tutorials are complete and correct. All code examples follow actual project patterns.

The primary issue is a stale tool count (17 vs actual 18) that propagated from CLAUDE.md into the architecture guide, and an even more stale count (15) in the getting started tutorial. The test count is also stale. These are straightforward number fixes.

No contradictions exist between docs and source code beyond the counts noted above. Terminology is consistent across all documents. The audit findings about undocumented patterns (write-through, retry, persistence) are fully addressed in the architecture guide and knowledge store tutorial.
