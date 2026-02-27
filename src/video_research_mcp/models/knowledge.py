"""Pydantic models for knowledge query tool responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeHit(BaseModel):
    """Single search result from a knowledge query."""

    collection: str = Field(description="Source collection name")
    object_id: str = Field(description="Weaviate object UUID")
    score: float = Field(default=0.0, description="Relevance score")
    properties: dict = Field(default_factory=dict, description="Object properties")


class KnowledgeSearchResult(BaseModel):
    """Result from knowledge_search."""

    query: str = Field(description="Original search query")
    total_results: int = Field(default=0, description="Total results returned")
    results: list[KnowledgeHit] = Field(default_factory=list)


class KnowledgeRelatedResult(BaseModel):
    """Result from knowledge_related."""

    source_id: str = Field(description="Source object UUID")
    source_collection: str = Field(description="Source collection name")
    related: list[KnowledgeHit] = Field(default_factory=list)


class CollectionStats(BaseModel):
    """Stats for a single collection."""

    name: str = Field(description="Collection name")
    count: int = Field(default=0, description="Object count")


class KnowledgeStatsResult(BaseModel):
    """Result from knowledge_stats."""

    collections: list[CollectionStats] = Field(default_factory=list)
    total_objects: int = Field(default=0, description="Sum of all collection counts")


class KnowledgeIngestResult(BaseModel):
    """Result from knowledge_ingest."""

    collection: str = Field(description="Target collection")
    object_id: str = Field(default="", description="Created object UUID")
    status: str = Field(default="success", description="Ingest status")
