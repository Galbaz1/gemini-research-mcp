"""Tests for model_dump(mode="json") correctness across tool returns."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from video_research_mcp.errors import make_tool_error
from video_research_mcp.tools.knowledge.helpers import serialize


class TestMakeToolErrorSerialization:
    """make_tool_error returns JSON-safe dicts."""

    def test_error_dict_is_json_serializable(self):
        """GIVEN any exception WHEN make_tool_error THEN result is JSON-serializable."""
        result = make_tool_error(RuntimeError("test error"))
        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed["error"] == "test error"
        assert "category" in parsed

    def test_none_fields_serialize(self):
        """retry_after_seconds=None serializes correctly."""
        result = make_tool_error(RuntimeError("test"))
        assert result["retry_after_seconds"] is None
        json.dumps(result)  # Should not raise


class TestSerializeHelper:
    """serialize() handles all Weaviate property types."""

    def test_datetime_to_isoformat(self):
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert serialize(dt) == "2025-01-01T00:00:00+00:00"

    def test_nested_dict(self):
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = serialize({"nested": {"date": dt, "value": 42}})
        assert result["nested"]["date"] == "2025-01-01T00:00:00+00:00"
        assert result["nested"]["value"] == 42

    def test_list_with_datetimes(self):
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = serialize([dt, "text", 42])
        assert result[0] == "2025-01-01T00:00:00+00:00"

    def test_plain_value_passthrough(self):
        assert serialize("hello") == "hello"
        assert serialize(42) == 42
        assert serialize(None) is None
