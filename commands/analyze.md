---
description: Analyze any content — URL, file, or pasted text
argument-hint: <url|file-path|text>
allowed-tools: mcp__gemini-research__content_analyze, mcp__gemini-research__content_extract, mcp__plugin_serena_serena__write_memory, mcp__plugin_serena_serena__list_memories
model: sonnet
---

# Content Analysis: $ARGUMENTS

Analyze the provided content (URL, file path, or text).

## Steps

1. Determine the input type from "$ARGUMENTS":
   - If it starts with `http://` or `https://`: use `content_analyze` with `url` parameter
   - If it looks like a file path (contains `/` or `.`extension): use `content_analyze` with `file_path` parameter
   - Otherwise: use `content_analyze` with `text` parameter
2. Use instruction="Provide a comprehensive analysis including title, summary, key points, important entities, document structure, and quality assessment."
3. Present results clearly:
   - **Title and Source**
   - **Summary** (2-3 sentences)
   - **Key Points** (bulleted)
   - **Entities** (people, organizations, concepts)
   - **Quality Assessment**
4. Offer to extract specific structured data with `content_extract` if the user needs a particular schema

## Save to Memory

After presenting results, check if `write_memory` is in your available tools.

### If `write_memory` IS available:

1. Generate a slug from the content title or source: lowercase, hyphens, max 50 chars (e.g., "Attention Is All You Need" → `attention-is-all-you-need`, a URL like `arxiv.org/abs/2401.12345` → `arxiv-2401-12345`)
2. Use `write_memory` with memory_name=`gr/analysis/<slug>` and content:

```markdown
# <Title>

> Analyzed on <today's date>
> Source: <url, file path, or "pasted text">

## Summary

<2-3 sentence summary>

## Key Points

<Bulleted key points>

## Entities

<People, organizations, and key concepts mentioned>
```

3. Confirm: **Saved to `gr/analysis/<slug>`** — browse past analyses with `/gr:recall analysis`

### If `write_memory` is NOT available:

Show this tip once, after the results:

> **Tip:** Want to save analyses across sessions? Install the Serena plugin:
> ```
> claude plugin install serena@claude-plugins-official
> ```
> Then restart Claude Code. Your future `/gr:analyze` results will be auto-saved and browsable via `/gr:recall`.
