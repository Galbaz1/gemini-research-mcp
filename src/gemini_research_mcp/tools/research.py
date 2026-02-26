"""Research tools — 3 tools on a FastMCP sub-server."""

from __future__ import annotations

import json
import logging

from fastmcp import FastMCP

from ..client import GeminiClient
from ..errors import make_tool_error
from ..models.research import (
    EvidenceAssessment,
    Finding,
    Phase,
    ResearchPlan,
    ResearchReport,
)
from ..prompts.research import (
    DEEP_RESEARCH_SYSTEM,
    EVIDENCE_ASSESSMENT,
    EVIDENCE_COLLECTION,
    RESEARCH_PLAN,
    SCOPE_DEFINITION,
    SYNTHESIS,
)

logger = logging.getLogger(__name__)
research_server = FastMCP("research")

# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_findings(text: str) -> list[Finding]:
    """Best-effort extraction of findings from Gemini's free-text response."""
    findings: list[Finding] = []
    tiers = ["CONFIRMED", "STRONG INDICATOR", "INFERENCE", "SPECULATION", "UNKNOWN"]
    current_claim = ""
    current_tier = "UNKNOWN"
    current_supporting: list[str] = []
    current_contradicting: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        # Detect evidence tier labels
        for t in tiers:
            if f"[{t}]" in stripped.upper():
                if current_claim:
                    findings.append(
                        Finding(
                            claim=current_claim,
                            evidence_tier=current_tier,
                            supporting=current_supporting,
                            contradicting=current_contradicting,
                        )
                    )
                current_claim = stripped.replace(f"[{t}]", "").strip().lstrip("- ").strip()
                current_tier = t
                current_supporting = []
                current_contradicting = []
                break
        else:
            if stripped.lower().startswith("supporting") or stripped.lower().startswith(
                "- support"
            ):
                current_supporting.append(stripped)
            elif stripped.lower().startswith("contradict") or stripped.lower().startswith(
                "- contra"
            ):
                current_contradicting.append(stripped)

    if current_claim:
        findings.append(
            Finding(
                claim=current_claim,
                evidence_tier=current_tier,
                supporting=current_supporting,
                contradicting=current_contradicting,
            )
        )
    return findings


# ── Tools ─────────────────────────────────────────────────────────────────────


@research_server.tool()
async def research_deep(
    topic: str,
    scope: str = "moderate",
    thinking_level: str = "high",
) -> dict:
    """Multi-phase deep research analysis with evidence-tier labeling.

    Phases: Scope Definition → Evidence Collection → Synthesis.
    Every claim is labeled [CONFIRMED], [STRONG INDICATOR], [INFERENCE],
    [SPECULATION], or [UNKNOWN].
    """
    try:
        # Phase 1: Scope
        scope_prompt = SCOPE_DEFINITION.format(topic=topic, scope=scope)
        scope_text = await GeminiClient.generate(
            scope_prompt,
            system_instruction=DEEP_RESEARCH_SYSTEM,
            thinking_level=thinking_level,
        )

        # Phase 2: Evidence collection
        evidence_prompt = EVIDENCE_COLLECTION.format(topic=topic, context=scope_text)
        evidence_text = await GeminiClient.generate(
            evidence_prompt,
            system_instruction=DEEP_RESEARCH_SYSTEM,
            thinking_level=thinking_level,
        )

        findings = _parse_findings(evidence_text)

        # Phase 3: Synthesis
        findings_text = (
            "\n".join(f"- [{f.evidence_tier}] {f.claim}" for f in findings) or evidence_text
        )

        synth_prompt = SYNTHESIS.format(topic=topic, findings_text=findings_text)
        synth_text = await GeminiClient.generate(
            synth_prompt,
            system_instruction=DEEP_RESEARCH_SYSTEM,
            thinking_level=thinking_level,
        )

        # Extract sections from synthesis
        lines = synth_text.split("\n")
        exec_summary = ""
        open_questions: list[str] = []
        methodology = ""
        in_section = ""
        for ln in lines:
            s = ln.strip()
            up = s.upper()
            if "EXECUTIVE SUMMARY" in up:
                in_section = "exec"
                continue
            if "OPEN QUESTION" in up:
                in_section = "oq"
                continue
            if "METHODOLOGY" in up or "CONFIDENCE" in up:
                in_section = "meth"
                continue
            if any(k in up for k in ["CROSS-CUTTING", "CONTRADICTION", "RECOMMENDATION"]):
                in_section = ""
                continue
            if in_section == "exec" and s:
                exec_summary += s + " "
            elif in_section == "oq" and s.startswith("-"):
                open_questions.append(s.lstrip("- "))
            elif in_section == "meth" and s:
                methodology += s + " "

        return ResearchReport(
            topic=topic,
            scope=scope,
            executive_summary=exec_summary.strip() or synth_text[:500],
            findings=findings,
            open_questions=open_questions,
            methodology_critique=methodology.strip(),
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@research_server.tool()
async def research_plan(
    topic: str,
    scope: str = "moderate",
    available_agents: int = 10,
) -> dict:
    """Generate a multi-agent research orchestration plan.

    Returns a phased blueprint with task decomposition and model assignments.
    Does NOT spawn agents — provides the blueprint for the caller.
    """
    try:
        prompt = RESEARCH_PLAN.format(topic=topic, scope=scope, available_agents=available_agents)
        resp = await GeminiClient.generate(
            prompt,
            system_instruction=DEEP_RESEARCH_SYSTEM,
            thinking_level="high",
        )

        # Try structured extraction
        schema = ResearchPlan.model_json_schema()
        try:
            structured = await GeminiClient.generate(
                f"Convert this research plan into the JSON schema below.\n\nPLAN:\n{resp}\n\nSCHEMA:\n{json.dumps(schema)}",
                thinking_level="low",
                response_schema=schema,
            )
            plan = ResearchPlan.model_validate_json(structured)
        except Exception:
            # Fallback: manual extraction
            plan = ResearchPlan(
                topic=topic,
                scope=scope,
                phases=[Phase(name="Full Plan", description=resp[:500], tasks=[])],
                task_decomposition=[resp],
            )

        return plan.model_dump()

    except Exception as exc:
        return make_tool_error(exc)


@research_server.tool()
async def research_assess_evidence(
    claim: str,
    sources: list[str],
    context: str = "",
) -> dict:
    """Assess a claim against sources, returning evidence tier + confidence."""
    try:
        sources_text = "\n".join(f"- {s}" for s in sources)
        prompt = EVIDENCE_ASSESSMENT.format(claim=claim, sources_text=sources_text, context=context)
        resp = await GeminiClient.generate(
            prompt,
            system_instruction=DEEP_RESEARCH_SYSTEM,
            thinking_level="high",
        )

        # Parse tier
        tier = "UNKNOWN"
        for t in ["CONFIRMED", "STRONG INDICATOR", "INFERENCE", "SPECULATION", "UNKNOWN"]:
            if f"[{t}]" in resp.upper() or t in resp.upper()[:200]:
                tier = t
                break

        # Parse confidence
        confidence = 0.5
        import re

        conf_match = re.search(r"CONFIDENCE\s*:\s*([\d.]+)", resp, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except ValueError:
                pass

        return EvidenceAssessment(
            claim=claim,
            tier=tier,
            confidence=confidence,
            reasoning=resp,
        ).model_dump()

    except Exception as exc:
        return make_tool_error(exc)
