"""Content analysis prompt templates."""

from __future__ import annotations

STRUCTURED_EXTRACT = """\
Extract structured data from the following content according to the provided schema.

CONTENT:
{content}

SCHEMA:
{schema_description}

Return a valid JSON object matching the schema exactly. Do not include any text outside \
the JSON object."""
