"""Tests for schema complexity guard."""

from __future__ import annotations

import pytest

from video_research_mcp.schema_guard import SchemaComplexityError, check_schema_complexity


class TestSchemaComplexity:
    def test_simple_schema_passes(self):
        """Flat schema with few properties passes all checks."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        check_schema_complexity(schema)

    def test_depth_exceeded(self):
        """Deeply nested schema raises SchemaComplexityError."""
        schema = {"type": "object", "properties": {
            "a": {"type": "object", "properties": {
                "b": {"type": "object", "properties": {
                    "c": {"type": "object", "properties": {
                        "d": {"type": "object", "properties": {
                            "e": {"type": "object", "properties": {
                                "f": {"type": "string"},
                            }},
                        }},
                    }},
                }},
            }},
        }}
        with pytest.raises(SchemaComplexityError, match="depth"):
            check_schema_complexity(schema, max_depth=5)

    def test_property_count_exceeded(self):
        """Schema with too many properties raises SchemaComplexityError."""
        props = {f"prop_{i}": {"type": "string"} for i in range(60)}
        schema = {"type": "object", "properties": props}
        with pytest.raises(SchemaComplexityError, match="properties"):
            check_schema_complexity(schema, max_properties=50)

    def test_enum_size_exceeded(self):
        """Enum with too many values raises SchemaComplexityError."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": [f"val_{i}" for i in range(25)]},
            },
        }
        with pytest.raises(SchemaComplexityError, match="Enum"):
            check_schema_complexity(schema, max_enum_size=20)

    def test_array_items_depth(self):
        """Array items contribute to depth measurement."""
        schema = {
            "type": "array",
            "items": {"type": "object", "properties": {
                "nested": {"type": "object", "properties": {
                    "deep": {"type": "object", "properties": {
                        "deeper": {"type": "object", "properties": {
                            "deepest": {"type": "object", "properties": {
                                "leaf": {"type": "string"},
                            }},
                        }},
                    }},
                }},
            }},
        }
        with pytest.raises(SchemaComplexityError, match="depth"):
            check_schema_complexity(schema, max_depth=4)

    def test_custom_limits(self):
        """Custom limits override defaults."""
        schema = {
            "type": "object",
            "properties": {f"p{i}": {"type": "string"} for i in range(10)},
        }
        with pytest.raises(SchemaComplexityError, match="properties"):
            check_schema_complexity(schema, max_properties=5)
        # With higher limit, it passes
        check_schema_complexity(schema, max_properties=20)
