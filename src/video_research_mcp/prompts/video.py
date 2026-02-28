"""Video analysis prompt templates — metadata-informed extraction.

Templates are used by tools/video.py to improve YouTube analysis quality:

1. METADATA_OPTIMIZER — sent to Flash to generate a tailored extraction prompt.
   Variables: {title}, {channel}, {category}, {duration}, {description_excerpt},
              {tags}, {instruction}.
2. METADATA_PREAMBLE — formats metadata as context prepended to the analysis.
   Variables: {title}, {channel}, {category}, {duration}, {tags}.
"""

from __future__ import annotations

METADATA_OPTIMIZER = """\
You are a video analysis prompt engineer. Given metadata about a YouTube video \
and the user's analysis instruction, produce a focused 2-4 sentence extraction \
prompt tailored to THIS specific video.

Video metadata:
- Title: {title}
- Channel: {channel}
- Category: {category}
- Duration: {duration}
- Tags: {tags}
- Description excerpt: {description_excerpt}

User instruction: {instruction}

Write a concise, specific prompt that tells a video analyzer exactly what to \
look for in this particular video. Reference the video's topic, format, and \
likely structure. Do NOT include generic instructions — be specific to this video."""

METADATA_PREAMBLE = (
    'Video context: "{title}" by {channel} ({category}, {duration}). Tags: {tags}'
)
