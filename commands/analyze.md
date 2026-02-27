---
name: analyze
description: Analyze any content — URL, file, or pasted text
argument-hint: <url|file-path|text>
allowed-tools: mcp__plugin_gemini-research_gemini-research__content_analyze, mcp__plugin_gemini-research_gemini-research__content_extract
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
