"""Tests for the coerce_json_param helper in types.py."""

from __future__ import annotations

from video_research_mcp.types import coerce_json_param


class TestCoerceJsonParamDict:
    """Coerce JSON string → dict."""

    def test_parses_json_string_to_dict(self):
        """GIVEN a JSON string encoding a dict,
        WHEN coerce_json_param is called with expected_type=dict,
        THEN it returns the parsed dict.
        """
        result = coerce_json_param('{"key": "value"}', dict)
        assert result == {"key": "value"}

    def test_passes_dict_through(self):
        """Native dict values pass through unchanged."""
        original = {"key": "value"}
        assert coerce_json_param(original, dict) is original

    def test_none_passes_through(self):
        """None is returned unchanged."""
        assert coerce_json_param(None, dict) is None

    def test_rejects_list_when_expecting_dict(self):
        """JSON list string is not coerced when expecting dict."""
        result = coerce_json_param('["a", "b"]', dict)
        assert result == '["a", "b"]'

    def test_invalid_json_returns_original(self):
        """Malformed JSON string is returned as-is."""
        result = coerce_json_param("{not json}", dict)
        assert result == "{not json}"

    def test_empty_dict_string(self):
        """Empty JSON object string is parsed."""
        assert coerce_json_param("{}", dict) == {}

    def test_nested_dict(self):
        """Nested JSON objects are parsed correctly."""
        result = coerce_json_param('{"a": {"b": 1}}', dict)
        assert result == {"a": {"b": 1}}


class TestCoerceJsonParamList:
    """Coerce JSON string → list."""

    def test_parses_json_string_to_list(self):
        """GIVEN a JSON string encoding a list,
        WHEN coerce_json_param is called with expected_type=list,
        THEN it returns the parsed list.
        """
        result = coerce_json_param('["a", "b", "c"]', list)
        assert result == ["a", "b", "c"]

    def test_passes_list_through(self):
        """Native list values pass through unchanged."""
        original = ["a", "b"]
        assert coerce_json_param(original, list) is original

    def test_none_passes_through(self):
        """None is returned unchanged."""
        assert coerce_json_param(None, list) is None

    def test_rejects_dict_when_expecting_list(self):
        """JSON dict string is not coerced when expecting list."""
        result = coerce_json_param('{"key": "val"}', list)
        assert result == '{"key": "val"}'

    def test_invalid_json_returns_original(self):
        """Malformed JSON string is returned as-is."""
        result = coerce_json_param("[not json", list)
        assert result == "[not json"

    def test_empty_list_string(self):
        """Empty JSON array string is parsed."""
        assert coerce_json_param("[]", list) == []
