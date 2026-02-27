---
description: Browse and recall past research, video notes, and analyses
argument-hint: [topic]
allowed-tools: mcp__plugin_serena_serena__list_memories, mcp__plugin_serena_serena__read_memory, mcp__plugin_serena_serena__delete_memory, mcp__plugin_serena_serena__rename_memory
model: sonnet
---

# Recall: $ARGUMENTS

Browse saved results from previous `/gr:*` commands.

## Behavior

### If no arguments given (`$ARGUMENTS` is empty):

1. Use `list_memories` with topic=`gr` to show all saved results
2. Group them by category and present as a clean list:

   **Research**
   - `gr/research/topic-slug` — <first line of content after title>

   **Video Notes**
   - `gr/video/video-slug` — <video title>

   **Video Chats**
   - `gr/video-chat/chat-slug` — <video title>

   **Analyses**
   - `gr/analysis/source-slug` — <content title>

3. Invite the user to pick one to read, or give a topic to filter

### If arguments given:

1. First try `list_memories` with topic=`gr/$ARGUMENTS` (e.g., `gr/research`) to check if it's a category filter
2. If that returns results, show them grouped as above
3. If no results, try `list_memories` with topic=`gr` and filter names containing "$ARGUMENTS" as a keyword search
4. If a single match is found, read it directly with `read_memory`
5. If multiple matches, list them and let the user pick
6. If no matches, tell the user: "No saved results matching '$ARGUMENTS'. Run `/gr:research`, `/gr:video`, or `/gr:analyze` to build your knowledge base."

## Management

If the user asks to delete or rename a memory, use `delete_memory` or `rename_memory` accordingly. Always confirm before deleting.
