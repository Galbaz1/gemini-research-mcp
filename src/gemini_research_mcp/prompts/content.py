"""Content analysis prompt templates."""

from __future__ import annotations

ANALYZE_DOCUMENT = """\
Analyze the following content thoroughly:

{content_description}

{focus_instruction}

Produce:
1. SUMMARY: Comprehensive overview (3-5 sentences)
2. KEY POINTS: The most important takeaways (bullet list)
3. STRUCTURE: How the content is organized
4. ENTITIES: Key people, organizations, technologies, or concepts mentioned
5. METHODOLOGY NOTES: If applicable, how conclusions were reached
6. QUALITY ASSESSMENT: Strengths and weaknesses of the content"""

SUMMARIZE = """\
Summarize the following content at {detail_level} detail level:

{content}

Detail level guidelines:
- brief: 2-3 sentences, only the essential point
- medium: 1-2 paragraphs, key points and context
- detailed: Full summary preserving important nuances and structure

Produce:
TEXT: [your summary]
KEY_TAKEAWAYS: takeaway1 | takeaway2 | takeaway3"""

STRUCTURED_EXTRACT = """\
Extract structured data from the following content according to the provided schema.

CONTENT:
{content}

SCHEMA:
{schema_description}

Return a valid JSON object matching the schema exactly. Do not include any text outside \
the JSON object."""

WEB_ANALYZE = """\
Analyze the content from this URL:

{prompt}

Provide a thorough analysis addressing the specific request above. Include relevant \
quotes or data points from the content."""
