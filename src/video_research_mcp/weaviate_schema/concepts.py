"""ConceptKnowledge and RelationshipEdges collections.

ConceptKnowledge tracks individual concepts extracted from analyses
with their knowledge state (know/fuzzy/unknown). RelationshipEdges
stores directed relationships between concepts.
"""

from __future__ import annotations

from .base import CollectionDef, PropertyDef, _common_properties


CONCEPT_KNOWLEDGE = CollectionDef(
    name="ConceptKnowledge",
    description="Concepts extracted from video and content analyses with knowledge states",
    properties=_common_properties() + [
        PropertyDef("concept_name", ["text"], "Name of the concept"),
        PropertyDef(
            "state", ["text"], "Knowledge state: know, fuzzy, or unknown",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "source_url", ["text"], "URL or path of the source content",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("source_title", ["text"], "Title of the source content"),
        PropertyDef(
            "source_category", ["text"], "Category: video, video-chat, research, analysis",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("description", ["text"], "Brief description of the concept"),
        PropertyDef(
            "timestamp", ["text"], "Timestamp in source where concept appears",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)

RELATIONSHIP_EDGES = CollectionDef(
    name="RelationshipEdges",
    description="Directed relationships between concepts from analyses",
    properties=_common_properties() + [
        PropertyDef("from_concept", ["text"], "Source concept name"),
        PropertyDef("to_concept", ["text"], "Target concept name"),
        PropertyDef(
            "relationship_type", ["text"], "Relationship type: enables, example_of, builds_on, contradicts, related_to",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "source_url", ["text"], "URL or path of the source content",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "source_category", ["text"], "Category: video, video-chat, research, analysis",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)
