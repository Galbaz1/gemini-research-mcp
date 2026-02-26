"""Shared Gemini client singleton with thinking-level support."""

from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from google.genai import types

from .config import get_config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Process-wide Gemini client pool (one client per API key)."""

    _clients: dict[str, genai.Client] = {}

    @classmethod
    def get(cls, api_key: str | None = None) -> genai.Client:
        """Return (or create) the shared client for *api_key*."""
        key = api_key or get_config().gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("No Gemini API key — set GEMINI_API_KEY or pass api_key explicitly")
        if key not in cls._clients:
            cls._clients[key] = genai.Client(api_key=key)
            logger.info("Created Gemini client (key …%s)", key[-4:])
        return cls._clients[key]

    @classmethod
    async def generate(
        cls,
        contents: Any,
        *,
        model: str | None = None,
        thinking_level: str | None = None,
        response_schema: dict | None = None,
        temperature: float | None = None,
        system_instruction: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Unified async generate with thinking + optional structured output.

        Returns the model's text response (thinking parts stripped).
        """
        cfg = get_config()
        resolved_model = model or cfg.default_model
        resolved_thinking = thinking_level or cfg.default_thinking_level

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=resolved_thinking),
            temperature=temperature if temperature is not None else cfg.default_temperature,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if response_schema:
            config.response_mime_type = "application/json"
            config.response_json_schema = response_schema

        client = cls.get()
        response = await client.aio.models.generate_content(
            model=resolved_model,
            contents=contents,
            config=config,
            **kwargs,
        )

        # Strip thinking parts — only return user-visible text
        parts = response.candidates[0].content.parts if response.candidates else []
        text_parts = [p.text for p in parts if p.text and not getattr(p, "thought", False)]
        return "\n".join(text_parts) if text_parts else (response.text or "")

    @classmethod
    async def close_all(cls) -> int:
        """Shut down all shared clients. Returns count closed."""
        count = 0
        for key, client in list(cls._clients.items()):
            try:
                await client.aio.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass
            count += 1
        cls._clients.clear()
        logger.info("Closed %d Gemini client(s)", count)
        return count
