"""Write-through store functions — one per Weaviate collection.

Each store_* function is called by its corresponding tool after a
successful Gemini response. All writes are fire-and-forget: failures
log a warning but never propagate to the tool caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import weaviate.util
from weaviate.classes.data import DataObject

from .config import get_config
from .weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    """Guard — returns False if Weaviate is not configured."""
    return get_config().weaviate_enabled


def _now() -> datetime:
    """Return current UTC datetime (Weaviate accepts datetime objects directly)."""
    return datetime.now(timezone.utc)


async def store_video_analysis(
    result: dict, content_id: str, instruction: str, source_url: str = ""
) -> str | None:
    """Persist a video_analyze result to the VideoAnalyses collection.

    Called by tools/video.py after a successful video_analyze or
    video_batch_analyze call.

    Args:
        result: Serialised VideoResult dict.
        content_id: YouTube video ID or file content hash.
        instruction: The analysis instruction used.
        source_url: Original URL or file path.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoAnalyses")
            uuid = collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "video_analyze",
                "video_id": content_id,
                "source_url": source_url,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "raw_result": json.dumps(result),
                "timestamps_json": json.dumps(result.get("timestamps", [])),
                "topics": result.get("topics", []),
                "sentiment": result.get("sentiment", ""),
            })
            # Cross-ref to VideoMetadata (non-fatal)
            if content_id:
                try:
                    meta_uuid = weaviate.util.generate_uuid5(content_id)
                    collection.data.reference_add(from_uuid=uuid, from_property="has_metadata", to=meta_uuid)
                except Exception:
                    pass
            return str(uuid)

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_content_analysis(
    result: dict, source: str, instruction: str
) -> str | None:
    """Persist a content_analyze result to the ContentAnalyses collection.

    Called by tools/content.py after a successful content_analyze call.

    Args:
        result: Serialised ContentResult dict.
        source: URL, file path, or "(text)" for inline text input.
        instruction: The analysis instruction used.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("ContentAnalyses")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "content_analyze",
                "source": source,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "entities": result.get("entities", []),
                "raw_result": json.dumps(result),
                "structure_notes": result.get("structure_notes", ""),
                "quality_assessment": result.get("quality_assessment", ""),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_research_finding(report_dict: dict) -> list[str] | None:
    """Persist a research_deep report to the ResearchFindings collection.

    Creates one object for the report-level summary and one per finding,
    all in the same collection. Called by tools/research.py after
    research_deep completes.

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

            # Build batch: report object + finding objects
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

            # Set report_uuid on findings and add cross-references
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

    Called by tools/research.py after research_plan completes.

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

    Stored in the same collection as research_deep findings but with
    source_tool="research_assess_evidence" for differentiation.
    Called by tools/research.py after research_assess_evidence completes.

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


async def store_video_metadata(meta_dict: dict) -> str | None:
    """Persist video_metadata result to the VideoMetadata collection.

    Uses a deterministic UUID derived from video_id so repeated fetches
    for the same video upsert (replace) rather than duplicate.
    Called by tools/youtube.py after video_metadata completes.

    Args:
        meta_dict: Serialised VideoMetadata dict.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _upsert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoMetadata")
            video_id = meta_dict.get("video_id", "")
            props = _meta_properties(meta_dict, video_id)

            if video_id:
                # Deterministic UUID from video_id — concurrent inserts converge
                det_uuid = weaviate.util.generate_uuid5(video_id)
                try:
                    collection.data.replace(uuid=det_uuid, properties=props)
                    return str(det_uuid)
                except Exception:
                    # Object doesn't exist yet — insert with deterministic UUID
                    return str(collection.data.insert(properties=props, uuid=det_uuid))

            return str(collection.data.insert(properties=props))

        return await asyncio.to_thread(_upsert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


def _meta_properties(meta_dict: dict, video_id: str) -> dict:
    """Build the Weaviate properties dict for a VideoMetadata insert/replace."""
    return {
        "created_at": _now(),
        "source_tool": "video_metadata",
        "video_id": video_id,
        "title": meta_dict.get("title", ""),
        "description": meta_dict.get("description", ""),
        "channel_title": meta_dict.get("channel_title", ""),
        "tags": meta_dict.get("tags", []),
        "view_count": meta_dict.get("view_count", 0),
        "like_count": meta_dict.get("like_count", 0),
        "duration": meta_dict.get("duration", ""),
        "published_at": meta_dict.get("published_at", ""),
        "channel_id": meta_dict.get("channel_id", ""),
        "comment_count": meta_dict.get("comment_count", 0),
        "duration_seconds": meta_dict.get("duration_seconds", 0),
        "category": meta_dict.get("category", ""),
        "definition": meta_dict.get("definition", ""),
        "has_captions": meta_dict.get("has_captions", False),
        "default_language": meta_dict.get("default_language", ""),
    }


async def store_session_turn(
    session_id: str, video_title: str, turn_index: int, prompt: str, response: str
) -> str | None:
    """Persist a video_continue_session turn to SessionTranscripts.

    Called by tools/video.py after each successful session turn.

    Args:
        session_id: The active session ID.
        video_title: Title of the video being discussed.
        turn_index: One-based turn number in the session.
        prompt: User's prompt for this turn.
        response: Model's response text.

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("SessionTranscripts")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "video_continue_session",
                "session_id": session_id,
                "video_title": video_title,
                "turn_index": turn_index,
                "turn_prompt": prompt,
                "turn_response": response,
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_web_search(
    query: str, response: str, sources: list[dict]
) -> str | None:
    """Persist a web_search result to the WebSearchResults collection.

    Called by tools/search.py after a successful web_search call.

    Args:
        query: The search query string.
        response: Gemini's grounded response text.
        sources: List of grounding source dicts (serialised to JSON).

    Returns:
        Weaviate object UUID, or None if disabled/failed.
    """
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("WebSearchResults")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "web_search",
                "query": query,
                "response": response,
                "sources_json": json.dumps(sources),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None
