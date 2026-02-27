"""Content analysis prompt templates.

Templates used by tools/content.py for structured extraction:

STRUCTURED_EXTRACT — used by content_extract to reshape raw content
into a caller-provided JSON schema. Variables: {content}, {schema_description}.
"""

from __future__ import annotations

STRUCTURED_EXTRACT = """\
Extract structured data from the following content according to the provided schema.

CONTENT:
{content}

SCHEMA:
{schema_description}

Return a valid JSON object matching the schema exactly. Do not include any text outside \
the JSON object."""
