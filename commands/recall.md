---
description: Browse and recall past research, video notes, and analyses
argument-hint: [topic]
allowed-tools: Glob, Grep, Read
model: sonnet
---

# Recall: $ARGUMENTS

Browse saved results from previous `/gr:*` commands.

## Find the Memory Directory

Use `Glob` on `~/.claude/projects/*/memory/gr/` to find saved results. There may be results across multiple project directories — check all of them.

## Behavior

### If no arguments given (`$ARGUMENTS` is empty):

1. Use `Glob` with pattern `~/.claude/projects/*/memory/gr/**/*.md` to find all saved results
2. Group them by category and present as a clean list:

   **Research** (`gr/research/`)
   - `topic-slug` — <first heading from file>

   **Video Notes** (`gr/video/`)
   - `video-slug` — <first heading from file>

   **Video Chats** (`gr/video-chat/`)
   - `chat-slug` — <first heading from file>

   **Analyses** (`gr/analysis/`)
   - `source-slug` — <first heading from file>

3. Show the total count and invite the user to pick one to read, or give a topic to filter

### If arguments match a category (`research`, `video`, `video-chat`, `analysis`):

1. Use `Glob` with pattern `~/.claude/projects/*/memory/gr/$ARGUMENTS/*.md`
2. List all results in that category with their titles (read first line of each file)

### If arguments are a keyword:

1. Use `Glob` to find all `gr/**/*.md` memory files
2. Use `Grep` to search file contents for "$ARGUMENTS"
3. If matches found, list them with the matching context
4. If a single match, read it directly with `Read`

### Reading a result:

When the user picks a result (by name or number), use `Read` to show the full content. Present it cleanly — it's already well-structured markdown.

## Management

If the user asks to delete a result, confirm first, then note the file path so they can remove it manually (commands cannot delete memory files). Suggest: `rm <path>`.
