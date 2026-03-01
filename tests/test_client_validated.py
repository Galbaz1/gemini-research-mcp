"""Tests for GeminiClient.generate_json_validated()."""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, Field

from video_research_mcp.client import GeminiClient


class SampleModel(BaseModel):
    name: str = Field(min_length=1)
    count: int = Field(ge=0)


class CoercionModel(BaseModel):
    """Model where Pydantic coerces types (str→int)."""
    value: int
    label: str = "default"


class TestGenerateJsonValidated:
    @pytest.mark.asyncio
    async def test_pydantic_schema_valid(self):
        """Valid JSON matching Pydantic model returns parsed dict."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"name": "test", "count": 5}),
        ):
            result = await GeminiClient.generate_json_validated(
                "test prompt", schema=SampleModel
            )
        assert result == {"name": "test", "count": 5}

    @pytest.mark.asyncio
    async def test_pydantic_schema_invalid_strict(self):
        """Invalid JSON with strict=True raises ValueError."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"name": "", "count": -1}),
        ):
            with pytest.raises(ValueError, match="Schema validation failed"):
                await GeminiClient.generate_json_validated(
                    "test prompt", schema=SampleModel, strict=True
                )

    @pytest.mark.asyncio
    async def test_pydantic_schema_invalid_lenient(self):
        """Invalid JSON with strict=False logs warning, returns dict anyway."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"name": "", "count": -1}),
        ):
            result = await GeminiClient.generate_json_validated(
                "test prompt", schema=SampleModel, strict=False
            )
        assert result["name"] == ""

    @pytest.mark.asyncio
    async def test_dict_schema_valid(self):
        """JSON Schema dict validates with jsonschema if installed."""
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"x": 42}),
        ):
            result = await GeminiClient.generate_json_validated(
                "test prompt", schema=schema
            )
        assert result["x"] == 42

    @pytest.mark.asyncio
    async def test_dict_schema_invalid_strict(self):
        """Invalid dict schema with strict=True raises ValueError."""
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"x": "not_an_int"}),
        ):
            with pytest.raises(ValueError, match="Schema validation failed"):
                await GeminiClient.generate_json_validated(
                    "test prompt", schema=schema, strict=True
                )

    @pytest.mark.asyncio
    async def test_non_json_response_strict(self):
        """Non-JSON response with strict=True raises ValueError."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value="not json at all",
        ):
            with pytest.raises(ValueError, match="non-JSON"):
                await GeminiClient.generate_json_validated(
                    "test prompt", schema=SampleModel, strict=True
                )

    @pytest.mark.asyncio
    async def test_non_json_response_lenient(self):
        """Non-JSON response with strict=False returns raw wrapper."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value="not json at all",
        ):
            result = await GeminiClient.generate_json_validated(
                "test prompt", schema=SampleModel, strict=False
            )
        assert "raw" in result

    @pytest.mark.asyncio
    async def test_pydantic_returns_coerced_output(self):
        """Validated output reflects Pydantic coercion (str→int, defaults)."""
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"value": "42"}),
        ):
            result = await GeminiClient.generate_json_validated(
                "test prompt", schema=CoercionModel
            )
        assert result["value"] == 42  # coerced from str "42"
        assert result["label"] == "default"  # filled by Pydantic default

    @pytest.mark.asyncio
    async def test_dict_schema_strict_without_jsonschema(self):
        """Strict mode + dict schema raises when jsonschema is not installed."""
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        with patch.object(
            GeminiClient, "generate", new_callable=AsyncMock,
            return_value=json.dumps({"x": 1}),
        ), patch.dict(sys.modules, {"jsonschema": None}):
            with pytest.raises(ValueError, match="jsonschema package required"):
                await GeminiClient.generate_json_validated(
                    "test prompt", schema=schema, strict=True
                )
