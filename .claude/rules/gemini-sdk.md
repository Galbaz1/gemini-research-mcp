---
paths: "src/**/*.py"
---

# Google GenAI SDK Patterns (>=1.57)

## Client

- Singleton via `GeminiClient.get()` — never construct `genai.Client()` directly
- All generation through `GeminiClient.generate()` or `.generate_structured()`
- Async API: `client.aio.models.generate_content()`

## Types

- Import from `google.genai import types`
- Key types: `types.Part`, `types.Content`, `types.GenerateContentConfig`, `types.ThinkingConfig`
- Build video parts: `types.Part.from_uri(file_uri=..., mime_type=...)`

## Thinking

- All calls include `ThinkingConfig(thinking_level=...)` via config
- Levels: "minimal", "low", "medium", "high"
- Strip thinking parts from responses: `getattr(p, "thought", False)` — this is intentional defensive code, not a compat shim

## Context Caching

- `cached_content` in `GenerateContentConfig` — cache name string
- Registry maps `(content_id, model)` → cache name
- Cache prewarm via `context_cache.start_prewarm()`, lookup via `lookup_or_await()`
- Caches expire via TTL (default 1 hour) — no manual cleanup needed on shutdown

## Models

- Default: `gemini-3.1-pro-preview` (config.py)
- Flash: `gemini-3-flash-preview`
- Model strings are preview/beta — this is intentional, we track latest Gemini
