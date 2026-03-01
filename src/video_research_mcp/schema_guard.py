"""Schema complexity guard — prevents Gemini structured output failures.

Gemini's structured output has undocumented limits on schema depth,
property count, and enum size. This module catches violations early
with clear error messages instead of opaque API failures.
"""

from __future__ import annotations


class SchemaComplexityError(ValueError):
    """Raised when a JSON schema exceeds Gemini's structured output limits."""


def check_schema_complexity(
    schema: dict,
    *,
    max_depth: int = 5,
    max_properties: int = 50,
    max_enum_size: int = 20,
) -> None:
    """Validate schema complexity against Gemini's structured output limits.

    Args:
        schema: JSON Schema dict to validate.
        max_depth: Maximum nesting depth allowed.
        max_properties: Maximum total properties across all levels.
        max_enum_size: Maximum number of values in any single enum.

    Raises:
        SchemaComplexityError: If any limit is exceeded.
    """
    depth = _measure_depth(schema)
    if depth > max_depth:
        raise SchemaComplexityError(
            f"Schema depth {depth} exceeds limit {max_depth}. "
            "Flatten nested objects or reduce nesting."
        )

    count = _count_properties(schema)
    if count > max_properties:
        raise SchemaComplexityError(
            f"Schema has {count} properties, exceeds limit {max_properties}. "
            "Simplify the schema or split into multiple calls."
        )

    _check_enums(schema, max_enum_size)


def _measure_depth(schema: dict, current: int = 0) -> int:
    """Recursively measure the maximum nesting depth of a JSON schema."""
    max_d = current

    if "properties" in schema:
        for prop in schema["properties"].values():
            max_d = max(max_d, _measure_depth(prop, current + 1))

    if "items" in schema and isinstance(schema["items"], dict):
        max_d = max(max_d, _measure_depth(schema["items"], current + 1))

    for key in ("allOf", "anyOf", "oneOf"):
        if key in schema:
            for sub in schema[key]:
                max_d = max(max_d, _measure_depth(sub, current))

    return max_d


def _count_properties(schema: dict) -> int:
    """Count total properties across all levels of a JSON schema."""
    count = len(schema.get("properties", {}))

    for prop in schema.get("properties", {}).values():
        count += _count_properties(prop)

    if "items" in schema and isinstance(schema["items"], dict):
        count += _count_properties(schema["items"])

    for key in ("allOf", "anyOf", "oneOf"):
        if key in schema:
            for sub in schema[key]:
                count += _count_properties(sub)

    return count


def _check_enums(schema: dict, max_size: int) -> None:
    """Raise SchemaComplexityError if any enum exceeds max_size."""
    if "enum" in schema and len(schema["enum"]) > max_size:
        raise SchemaComplexityError(
            f"Enum has {len(schema['enum'])} values, exceeds limit {max_size}."
        )

    for prop in schema.get("properties", {}).values():
        _check_enums(prop, max_size)

    if "items" in schema and isinstance(schema["items"], dict):
        _check_enums(schema["items"], max_size)

    for key in ("allOf", "anyOf", "oneOf"):
        if key in schema:
            for sub in schema[key]:
                _check_enums(sub, max_size)
