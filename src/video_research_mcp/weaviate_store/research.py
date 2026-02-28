"""Store functions for ResearchFindings and ResearchPlans collections."""

from __future__ import annotations

import asyncio
import json

from weaviate.classes.data import DataObject

from ..weaviate_client import WeaviateClient
from ._base import _is_enabled, _now, logger


async def store_research_finding(report_dict: dict) -> list[str] | None:
    """Persist a research_deep report to the ResearchFindings collection.

    Creates one object for the report-level summary and one per finding,
    all in the same collection.

    Args:
        report_dict: Serialised ResearchReport dict.

    Returns:
        List of Weaviate object UUIDs (report + findings), or None.
    """
    if not _is_enabled():
        return None
    try:
        def _insert_all():
            client = WeaviateClient.get()
            collection = client.collections.get("ResearchFindings")
            now = _now()
            topic = report_dict.get("topic", "")
            scope = report_dict.get("scope", "")

            report_props = {
                "created_at": now,
                "source_tool": "research_deep",
                "topic": topic,
                "scope": scope,
                "claim": "",
                "evidence_tier": "",
                "reasoning": "",
                "executive_summary": report_dict.get("executive_summary", ""),
                "confidence": 0.0,
                "open_questions": report_dict.get("open_questions", []),
                "supporting": [],
                "contradicting": [],
                "methodology_critique": report_dict.get("methodology_critique", ""),
                "recommendations": report_dict.get("recommendations", []),
                "report_uuid": "",
            }
            objects = [DataObject(properties=report_props)]

            for finding in report_dict.get("findings", []):
                objects.append(DataObject(properties={
                    "created_at": now,
                    "source_tool": "research_deep",
                    "topic": topic,
                    "scope": scope,
                    "claim": finding.get("claim", ""),
                    "evidence_tier": finding.get("evidence_tier", ""),
                    "reasoning": finding.get("reasoning", ""),
                    "executive_summary": "",
                    "confidence": finding.get("confidence", 0.0),
                    "open_questions": [],
                    "supporting": finding.get("supporting", []),
                    "contradicting": finding.get("contradicting", []),
                    "methodology_critique": "",
                    "recommendations": [],
                    "report_uuid": "",
                }))

            result = collection.data.insert_many(objects)
            uuids = [str(obj.uuid) for obj in result.all_objects]

            if len(uuids) > 1:
                report_uuid = uuids[0]
                for finding_uuid in uuids[1:]:
                    try:
                        collection.data.update(uuid=finding_uuid, properties={"report_uuid": report_uuid})
                        collection.data.reference_add(
                            from_uuid=finding_uuid, from_property="belongs_to_report", to=report_uuid,
                        )
                    except Exception:
                        pass

            return uuids

        return await asyncio.to_thread(_insert_all)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_research_plan(plan_dict: dict) -> str | None:
    """Persist a research_plan result to the ResearchPlans collection.

    Args:
        plan_dict: Serialised ResearchPlan dict.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("ResearchPlans")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "research_plan",
                "topic": plan_dict.get("topic", ""),
                "scope": plan_dict.get("scope", ""),
                "task_decomposition": plan_dict.get("task_decomposition", []),
                "phases_json": json.dumps(plan_dict.get("phases", [])),
                "recommended_models_json": json.dumps(plan_dict.get("recommended_models", [])),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_evidence_assessment(assessment_dict: dict) -> str | None:
    """Persist a research_assess_evidence result to ResearchFindings.

    Args:
        assessment_dict: Serialised EvidenceAssessment dict.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("ResearchFindings")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "research_assess_evidence",
                "topic": "",
                "scope": "",
                "claim": assessment_dict.get("claim", ""),
                "evidence_tier": assessment_dict.get("tier", ""),
                "reasoning": assessment_dict.get("reasoning", ""),
                "executive_summary": "",
                "confidence": assessment_dict.get("confidence", 0.0),
                "open_questions": [],
                "supporting": assessment_dict.get("supporting", []),
                "contradicting": assessment_dict.get("contradicting", []),
                "methodology_critique": "",
                "recommendations": [],
                "report_uuid": "",
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
