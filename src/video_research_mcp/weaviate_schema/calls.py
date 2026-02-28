"""CallNotes collection — meeting and call recording analysis.

Stores structured notes from call/meeting recordings, including
participants, decisions, action items, and discussion topics.
"""

from __future__ import annotations

from .base import CollectionDef, PropertyDef, _common_properties


CALL_NOTES = CollectionDef(
    name="CallNotes",
    description="Structured notes from meeting and call recordings",
    properties=_common_properties() + [
        PropertyDef(
            "video_id", ["text"], "YouTube video ID or file hash",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "source_url", ["text"], "Source URL or file path",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef("title", ["text"], "Meeting/call title"),
        PropertyDef("summary", ["text"], "Meeting summary"),
        PropertyDef("participants", ["text[]"], "Meeting participants"),
        PropertyDef("decisions", ["text[]"], "Decisions made during the meeting"),
        PropertyDef("action_items", ["text[]"], "Action items from the meeting"),
        PropertyDef("topics_discussed", ["text[]"], "Topics discussed"),
        PropertyDef(
            "duration", ["text"], "Meeting duration",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "meeting_date", ["text"], "Date of the meeting",
            skip_vectorization=True, index_searchable=False,
        ),
        PropertyDef(
            "local_filepath", ["text"], "Local filesystem path to the call recording file",
            skip_vectorization=True, index_searchable=False,
        ),
    ],
)
