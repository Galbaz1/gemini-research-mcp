"""Write-through store functions — one per Weaviate collection."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import weaviate.util

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
    """Store a video analysis result. Returns UUID or None."""
    if not _is_enabled():
        return None
    try:
        def _insert():
            client = WeaviateClient.get()
            collection = client.collections.get("VideoAnalyses")
            return str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "video_analyze",
                "video_id": content_id,
                "source_url": source_url,
                "instruction": instruction,
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "raw_result": json.dumps(result),
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_content_analysis(
    result: dict, source: str, instruction: str
) -> str | None:
    """Store a content analysis result. Returns UUID or None."""
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
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_research_finding(report_dict: dict) -> list[str] | None:
    """Store a research report + each finding as separate objects. Returns UUIDs or None."""
    if not _is_enabled():
        return None
    try:
        def _insert_all():
            client = WeaviateClient.get()
            collection = client.collections.get("ResearchFindings")
            uuids = []

            report_uuid = str(collection.data.insert(properties={
                "created_at": _now(),
                "source_tool": "research_deep",
                "topic": report_dict.get("topic", ""),
                "scope": report_dict.get("scope", ""),
                "claim": "",
                "evidence_tier": "",
                "reasoning": "",
                "executive_summary": report_dict.get("executive_summary", ""),
                "confidence": 0.0,
                "open_questions": report_dict.get("open_questions", []),
            }))
            uuids.append(report_uuid)

            for finding in report_dict.get("findings", []):
                finding_uuid = str(collection.data.insert(properties={
                    "created_at": _now(),
                    "source_tool": "research_deep",
                    "topic": report_dict.get("topic", ""),
                    "scope": report_dict.get("scope", ""),
                    "claim": finding.get("claim", ""),
                    "evidence_tier": finding.get("evidence_tier", ""),
                    "reasoning": finding.get("reasoning", ""),
                    "executive_summary": "",
                    "confidence": finding.get("confidence", 0.0),
                    "open_questions": [],
                }))
                uuids.append(finding_uuid)

            return uuids

        return await asyncio.to_thread(_insert_all)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_research_plan(plan_dict: dict) -> str | None:
    """Store a research plan. Returns UUID or None."""
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
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_evidence_assessment(assessment_dict: dict) -> str | None:
    """Store an evidence assessment as a research finding. Returns UUID or None."""
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
            }))

        return await asyncio.to_thread(_insert)
    except Exception as exc:
        logger.warning("Weaviate store failed (non-fatal): %s", exc)
        return None


async def store_video_metadata(meta_dict: dict) -> str | None:
    """Store video metadata with deterministic UUID for dedup. Returns UUID or None."""
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
    """Build properties dict for VideoMetadata collection."""
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
    }


async def store_session_turn(
    session_id: str, video_title: str, turn_index: int, prompt: str, response: str
) -> str | None:
    """Store a session turn. Returns UUID or None."""
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
    """Store a web search result. Returns UUID or None."""
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
