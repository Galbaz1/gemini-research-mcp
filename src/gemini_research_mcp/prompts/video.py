"""Video analysis prompt templates — 3 modes x 3 prompt tasks."""

from __future__ import annotations

# ── General mode ──────────────────────────────────────────────────────────────

GENERAL_TITLE_SUMMARY = """\
Analyze this video and provide:
1. A descriptive title (if not obvious from the video, create one based on content)
2. A comprehensive summary (3-5 sentences)

Format your response exactly as:
TITLE: [title here]
SUMMARY: [summary here]"""

GENERAL_KEY_MOMENTS = """\
Identify the 3-5 most important moments in this video.
For each moment provide the timestamp (MM:SS) and a brief description.

Format each moment as: [MM:SS] Description

Only output the moments, nothing else."""

GENERAL_THEMES_SENTIMENT = """\
Analyze this video and identify:
1. Main themes (list 3-5 keywords/phrases)
2. Overall sentiment/tone (one sentence)

Format as plain text (no markdown):
THEMES: theme1, theme2, theme3
SENTIMENT: [description]"""

# ── Tutorial mode ─────────────────────────────────────────────────────────────

TUTORIAL_TITLE_SUMMARY = """\
Analyze this technical tutorial video and provide:
1. A descriptive title that captures the tutorial's main topic
2. A summary explaining what viewers will learn (3-5 sentences)

Format your response exactly as:
TITLE: [title here]
SUMMARY: [summary here]"""

TUTORIAL_COMMANDS_TOOLS = """\
Extract ALL commands, tools, and technologies demonstrated in this tutorial.

Focus on VISUAL content - read what's typed in terminals, shown in editors, displayed on screen.

Format as plain text:
COMMANDS: command1, command2, command3
TOOLS: tool1, tool2, tool3

Only list items actually shown or demonstrated, not just mentioned."""

TUTORIAL_WORKFLOW_STEPS = """\
Extract the step-by-step workflow demonstrated in this tutorial.

For each step provide:
[MM:SS] What action is taken and what the expected result is

Focus on actionable steps viewers can replicate. Include any code or commands shown.
List 5-10 key steps maximum."""

# ── Claude Code mode ──────────────────────────────────────────────────────────

CLAUDE_CODE_TITLE_SUMMARY = """\
You are extracting knowledge for intermediate-to-advanced developers who want to \
MASTER Claude Code. They don't need basic explanations - they need SPECIFIC, ACTIONABLE techniques.

Analyze this Claude Code video and provide:

1. TITLE: A specific title describing the technique/workflow shown \
(not generic like "using Claude Code")

2. SUMMARY: Write 4-6 sentences that answer:
   - What SPECIFIC technique or workflow pattern is demonstrated?
   - What CONCRETE problem does it solve?
   - What is the KEY INSIGHT that makes this approach work?
   - What would a developer DO DIFFERENTLY after watching this?

DO NOT write generic statements like "demonstrates how to use Claude Code for tasks".
Instead write specifics like "Shows how to parallelize feature development by spawning \
3 sub-agents via the Task tool, each working in separate git worktrees to avoid merge conflicts."

Format your response exactly as:
TITLE: [specific title]
SUMMARY: [actionable summary with concrete details]"""

CLAUDE_CODE_COMMANDS_SHORTCUTS = """\
Extract EVERY Claude Code command, shortcut, and configuration shown in this video.

TARGET AUDIENCE: Developers who want to replicate these exact techniques.

For each item, extract the EXACT syntax as shown on screen:

COMMANDS (CLI and slash commands):
- `claude` invocations with flags (e.g., `claude --dangerously-skip-permissions`)
- Slash commands with full syntax (e.g., `/review --security`, `/plan`, `/resume`)
- Any command-line patterns shown

KEYBOARD SHORTCUTS:
- Key combinations with their actions (e.g., "Shift+Tab: Enter plan mode")
- Terminal shortcuts demonstrated

CONFIGURATION SHOWN:
- CLAUDE.md content/structure shown
- .claude/ directory contents (commands/, agents/, hooks/)
- settings.json or .mcp.json snippets
- Any file paths or directory structures mentioned

MCP SERVERS:
- Server names configured (e.g., "github", "filesystem", "postgres")
- How they're used in the workflow

Format as:
COMMANDS: exact command 1 | exact command 2 | exact command 3
SHORTCUTS: shortcut1 (action) | shortcut2 (action)
CONFIG: configuration detail 1 | configuration detail 2
MCP: server1 (usage) | server2 (usage)

Be EXHAUSTIVE - capture everything shown on screen."""

CLAUDE_CODE_WORKFLOW_FEATURES = """\
Extract the COMPLETE workflow demonstrated, with enough detail that a developer can \
replicate it WITHOUT watching the video.

TARGET AUDIENCE: Intermediate-to-advanced developers mastering agentic coding patterns.

For each workflow step, capture:
1. [TIMESTAMP] The exact action taken
2. WHY this step matters (the insight/reasoning)
3. Any specific syntax, file content, or configuration shown

SPECIFICALLY LOOK FOR:

AGENTIC PATTERNS:
- Sub-agent spawning: How are parallel agents launched? What prompts are used?
- Task decomposition: How is work split between agents?
- Git worktrees: Are they used? How are they set up?
- Plan mode vs execution: When does the presenter switch between them?

CONFIGURATION TECHNIQUES:
- CLAUDE.md structure: What sections are shown? What makes it effective?
- Custom commands: Any .claude/commands/ files created?
- Hooks: Any automation triggered by tool use?

PROMPTING STRATEGIES:
- How does the presenter phrase requests to Claude?
- What makes their prompts effective?
- Any prompt patterns that get better results?

WORKFLOW ORCHESTRATION:
- How are multiple features/tasks managed?
- How is context maintained across sessions?
- How are results from sub-agents combined?

Format each step as:
[MM:SS] **Action**: Specific description
  - Detail: Why this works / configuration shown / exact syntax used

List 8-15 steps with full detail. Include exact prompts/commands when shown."""

# ── Transcript extraction ─────────────────────────────────────────────────────

TRANSCRIPT_EXTRACT = """\
Transcribe this video with timestamps. For each segment of speech, provide the \
timestamp and the spoken text.

Format as:
[MM:SS] Spoken text here

Include all dialogue. Maintain speaker attribution if multiple speakers are present."""

# ── Comparison ────────────────────────────────────────────────────────────────

COMPARISON_TEMPLATE = """\
Compare the following video analyses and identify:

1. COMMON THEMES: Topics, techniques, or concepts shared across videos
2. COMMON COMMANDS: Commands or tools that appear in multiple videos
3. UNIQUE PER VIDEO: What each video covers that others don't
4. RECOMMENDATION: Which video to watch first and why

{analyses_text}

Format as:
COMMON_THEMES: theme1, theme2, theme3
COMMON_COMMANDS: cmd1, cmd2
UNIQUE: [video title] - unique aspect 1, unique aspect 2
RECOMMENDATION: [your recommendation]"""

# ── Prompt registry ───────────────────────────────────────────────────────────

PROMPTS: dict[str, dict[str, str]] = {
    "general": {
        "title_summary": GENERAL_TITLE_SUMMARY,
        "key_moments": GENERAL_KEY_MOMENTS,
        "themes_sentiment": GENERAL_THEMES_SENTIMENT,
    },
    "tutorial": {
        "title_summary": TUTORIAL_TITLE_SUMMARY,
        "commands_tools": TUTORIAL_COMMANDS_TOOLS,
        "workflow_steps": TUTORIAL_WORKFLOW_STEPS,
    },
    "claude_code": {
        "title_summary": CLAUDE_CODE_TITLE_SUMMARY,
        "commands_shortcuts": CLAUDE_CODE_COMMANDS_SHORTCUTS,
        "workflow_features": CLAUDE_CODE_WORKFLOW_FEATURES,
    },
}
