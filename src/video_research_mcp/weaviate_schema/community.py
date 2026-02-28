"""CommunityReactions collection — YouTube comment sentiment analysis.

Stores aggregated community sentiment from comment-analyst agent runs.
Each object represents one video's comment analysis with sentiment
distribution, themes, and notable opinions.
"""

from __future__ import annotations

from .base import CollectionDef, PropertyDef, ReferenceDef, _common_properties


COMMUNITY_REACTIONS = CollectionDef(
    name="CommunityReactions",
    description="YouTube comment sentiment analysis from comment-analyst agent",
    properties=_common_properties() + [
        PropertyDef(
            "video_id", ["text"], "YouTube video ID",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("video_title", ["text"], "Video title"),
        PropertyDef(
            "comment_count", ["int"], "Number of comments analyzed",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "sentiment_positive", ["number"], "Positive sentiment percentage 0-100",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "sentiment_negative", ["number"], "Negative sentiment percentage 0-100",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef(
            "sentiment_neutral", ["number"], "Neutral sentiment percentage 0-100",
            skip_vectorization=True, index_range_filters=True,
        ),
        PropertyDef("themes_positive", ["text[]"], "Positive themes from comments"),
        PropertyDef("themes_critical", ["text[]"], "Critical themes from comments"),
        PropertyDef("consensus", ["text"], "Overall community consensus assessment"),
        PropertyDef(
            "notable_opinions_json", ["text"], "Notable opinions as JSON array",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
    references=[
        ReferenceDef("for_video", "VideoMetadata", "Link to the analyzed video"),
    ],
)
