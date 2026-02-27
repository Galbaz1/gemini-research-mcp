---
description: Analyze any content — URL, file, or pasted text
argument-hint: <url|file-path|text>
allowed-tools: mcp__gemini-research__content_analyze, mcp__gemini-research__content_extract, Write, Glob, Read
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

After presenting results, auto-save to the project's memory directory for future reference.

1. Determine the memory directory: find the `.claude/` project memory path for the current working directory. Use `Glob` on `~/.claude/projects/*/memory/` to find the active project memory path if needed.
2. Generate a slug from the content title or source: lowercase, hyphens, no special chars, max 50 chars (e.g., "Attention Is All You Need" → `attention-is-all-you-need`, a URL like `arxiv.org/abs/2401.12345` → `arxiv-2401-12345`)
3. Use `Write` to save the file at `<memory-dir>/gr/analysis/<slug>.md`:

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

4. Confirm: **Saved to `gr/analysis/<slug>`** — browse past analyses with `/gr:recall analysis`
