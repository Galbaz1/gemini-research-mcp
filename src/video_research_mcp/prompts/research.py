"""Research tool prompt templates — deep analysis phases + evidence assessment."""

from __future__ import annotations

DEEP_RESEARCH_SYSTEM = """\
You are a non-sycophantic research analyst. Your job is critical analysis, not validation.

Rules:
- State flaws directly without softening language
- Challenge assumptions rather than confirm beliefs
- Never use phrases like "Great question!" or "You're absolutely right"
- Support critiques with reasoning and evidence
- Distinguish between critical issues and minor concerns
- Label ALL claims with evidence tiers: [CONFIRMED], [STRONG INDICATOR], [INFERENCE], \
[SPECULATION], [UNKNOWN]"""

SCOPE_DEFINITION = """\
Define the research scope for the following topic:

TOPIC: {topic}
SCOPE LEVEL: {scope}

Produce:
1. RESTATED QUESTION: Precise reformulation of the research question
2. STAKEHOLDERS: Who cares about this answer and why
3. CONSTRAINTS: What limits the research (time, access, domain)
4. SUCCESS CRITERIA: What would a complete answer look like
5. KNOWN UNKNOWNS: What we already know we don't know

Be specific. Avoid generic statements."""

EVIDENCE_COLLECTION = """\
Analyze the following topic deeply. For each finding:

TOPIC: {topic}
CONTEXT: {context}

For EACH claim or finding:
1. State the claim clearly
2. Label its evidence tier: [CONFIRMED], [STRONG INDICATOR], [INFERENCE], [SPECULATION], [UNKNOWN]
3. List supporting evidence
4. List contradicting evidence
5. Explain your reasoning for the tier assignment

Also produce:
- METHODOLOGY CRITIQUE: What methods were used and their limitations
- OPEN QUESTIONS: What remains unanswered
- ASSUMPTION MAP: Every assumption, rated by fragility (low/medium/high)
- FAILURE MODES: Realistic scenarios where the conclusions fail"""

SYNTHESIS = """\
Synthesize the following research findings into a coherent analysis:

TOPIC: {topic}
FINDINGS:
{findings_text}

Produce:
1. EXECUTIVE SUMMARY: 3-5 sentences covering the key takeaway
2. CROSS-CUTTING PATTERNS: Themes that appear across multiple findings
3. CONTRADICTIONS: Where findings disagree and why
4. CONFIDENCE ASSESSMENT: Overall confidence in the conclusions
5. RECOMMENDATIONS: What to do next based on this analysis
6. OPEN QUESTIONS: What still needs investigation

Label all claims with evidence tiers."""

RESEARCH_PLAN = """\
Create a research execution plan for the following topic:

TOPIC: {topic}
SCOPE: {scope}
AVAILABLE AGENTS: {available_agents}

Produce a phased plan:
1. PHASES: Name each phase, describe what it does, list specific tasks
2. MODEL ASSIGNMENT: Which model tier (haiku/sonnet/opus) for each phase
3. TASK DECOMPOSITION: Break into independent parallel tasks where possible
4. DEPENDENCIES: What must finish before what
5. ESTIMATED SCOPE: How many agents per phase

Rules:
- Haiku for bulk scanning, keyword extraction, fact-checking
- Sonnet for methodology analysis, domain synthesis, comparing approaches
- Opus for final integration, cross-domain insights, critical analysis
- Maximize parallelism within each phase
- Each task must be narrow and well-defined"""

EVIDENCE_ASSESSMENT = """\
Assess the following claim against the provided sources:

CLAIM: {claim}
SOURCES: {sources_text}
ADDITIONAL CONTEXT: {context}

Produce:
1. EVIDENCE TIER: [CONFIRMED] | [STRONG INDICATOR] | [INFERENCE] | [SPECULATION] | [UNKNOWN]
2. CONFIDENCE: 0.0 to 1.0
3. SUPPORTING EVIDENCE: What supports this claim (with source attribution)
4. CONTRADICTING EVIDENCE: What contradicts this claim (with source attribution)
5. REASONING: Step-by-step explanation of your assessment
6. CAVEATS: What could change this assessment"""
