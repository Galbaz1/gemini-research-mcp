"""Knowledge tool models — response schemas for Weaviate-backed tools.

Output schemas for knowledge_search, knowledge_related, knowledge_stats,
knowledge_ingest, knowledge_fetch, knowledge_ask, and knowledge_query tools.
Populated from Weaviate query responses, not from Gemini structured output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeHit(BaseModel):
    """Single search result from a Weaviate vector or hybrid query.

    Used as an item type in KnowledgeSearchResult and KnowledgeRelatedResult.
    """

    collection: str = Field(description="Source collection name")
    object_id: str = Field(description="Weaviate object UUID")
    score: float = Field(default=0.0, description="Relevance score")
    properties: dict = Field(default_factory=dict, description="Object properties")


class KnowledgeSearchResult(BaseModel):
    """Output schema for knowledge_search.

    Wraps hybrid (vector + keyword) search results from Weaviate.
    """

    query: str = Field(description="Original search query")
    total_results: int = Field(default=0, description="Total results returned")
    results: list[KnowledgeHit] = Field(default_factory=list)
    filters_applied: dict[str, str] | None = Field(default=None, description="Active filters")


class KnowledgeRelatedResult(BaseModel):
    """Output schema for knowledge_related.

    Returns objects semantically similar to a given source object.
    """

    source_id: str = Field(description="Source object UUID")
    source_collection: str = Field(description="Source collection name")
    related: list[KnowledgeHit] = Field(default_factory=list)


class CollectionStats(BaseModel):
    """Stats for a single collection."""

    name: str = Field(description="Collection name")
    count: int = Field(default=0, description="Object count")
    groups: dict[str, int] | None = Field(default=None, description="Counts grouped by property value")


class KnowledgeStatsResult(BaseModel):
    """Output schema for knowledge_stats.

    Reports object counts per Weaviate collection and a total across all.
    """

    collections: list[CollectionStats] = Field(default_factory=list)
    total_objects: int = Field(default=0, description="Sum of all collection counts")


class KnowledgeIngestResult(BaseModel):
    """Output schema for knowledge_ingest.

    Confirms insertion of a new object into a Weaviate collection.
    """

    collection: str = Field(description="Target collection")
    object_id: str = Field(default="", description="Created object UUID")
    status: str = Field(default="success", description="Ingest status")


class KnowledgeFetchResult(BaseModel):
    """Output schema for knowledge_fetch.

    Returns a single object retrieved by UUID from a specific collection.
    """

    collection: str = Field(description="Source collection name")
    object_id: str = Field(description="Weaviate object UUID")
    found: bool = Field(default=False, description="Whether the object was found")
    properties: dict = Field(default_factory=dict, description="Object properties")


class KnowledgeAskSource(BaseModel):
    """Source reference from QueryAgent ask mode."""

    collection: str = Field(description="Source collection name")
    object_id: str = Field(description="Source object UUID")


class KnowledgeAskResult(BaseModel):
    """Output schema for knowledge_ask — AI-generated answer with source citations."""

    query: str = Field(description="Original question")
    answer: str = Field(default="", description="AI-generated answer")
    sources: list[KnowledgeAskSource] = Field(default_factory=list)


class KnowledgeQueryResult(BaseModel):
    """Output schema for knowledge_query — natural language object retrieval."""

    query: str = Field(description="Original search query")
    total_results: int = Field(default=0)
    results: list[KnowledgeHit] = Field(default_factory=list)
