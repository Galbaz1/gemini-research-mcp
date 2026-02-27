"""Research tool models — structured output schemas for Gemini."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single research finding with evidence tier."""

    claim: str
    evidence_tier: str = (
        "UNKNOWN"  # CONFIRMED | STRONG INDICATOR | INFERENCE | SPECULATION | UNKNOWN
    )
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    reasoning: str = ""


class FindingsContainer(BaseModel):
    """Wrapper for structured extraction of multiple findings."""

    findings: list[Finding] = Field(default_factory=list)


class ResearchSynthesis(BaseModel):
    """Structured output for the synthesis phase of deep research."""

    executive_summary: str = ""
    open_questions: list[str] = Field(default_factory=list)
    methodology_critique: str = ""
    recommendations: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    """Output of a deep research analysis."""

    topic: str
    scope: str = "moderate"
    executive_summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    methodology_critique: str = ""


class Phase(BaseModel):
    """A single phase in a research plan."""

    name: str
    description: str
    tasks: list[str] = Field(default_factory=list)
    recommended_model: str = "haiku"


class ResearchPlan(BaseModel):
    """Orchestration blueprint for multi-agent research."""

    topic: str
    scope: str
    phases: list[Phase] = Field(default_factory=list)
    recommended_models: dict[str, str] = Field(default_factory=dict)
    task_decomposition: list[str] = Field(default_factory=list)


class EvidenceAssessment(BaseModel):
    """Assessment of a specific claim against sources."""

    claim: str
    tier: str = "UNKNOWN"
    confidence: float = 0.0
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    reasoning: str = ""
