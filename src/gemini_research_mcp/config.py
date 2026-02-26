"""Server configuration via environment variables."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Runtime configuration resolved from environment."""

    gemini_api_key: str = Field(default="")
    default_model: str = Field(default="gemini-3.1-pro-preview")
    flash_model: str = Field(default="gemini-3-flash-preview")
    default_thinking_level: str = Field(default="high")
    default_temperature: float = Field(default=1.0)
    cache_dir: str = Field(default="")
    cache_ttl_days: int = Field(default=30)
    max_sessions: int = Field(default=50)
    session_timeout_hours: int = Field(default=2)

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Build config from environment variables."""
        from pathlib import Path

        cache_default = str(Path.home() / ".cache" / "gemini-research-mcp")
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            default_model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            flash_model=os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash-preview"),
            default_thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "high"),
            default_temperature=float(os.getenv("GEMINI_TEMPERATURE", "1.0")),
            cache_dir=os.getenv("GEMINI_CACHE_DIR", cache_default),
            cache_ttl_days=int(os.getenv("GEMINI_CACHE_TTL_DAYS", "30")),
            max_sessions=int(os.getenv("GEMINI_MAX_SESSIONS", "50")),
            session_timeout_hours=int(os.getenv("GEMINI_SESSION_TIMEOUT_HOURS", "2")),
        )


# Singleton — initialised once at import time.
_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Return the global config singleton, creating it on first access."""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
    return _config


def update_config(**overrides: object) -> ServerConfig:
    """Patch the live config (used by ``infra_configure`` tool)."""
    global _config
    cfg = get_config()
    data = cfg.model_dump()
    data.update({k: v for k, v in overrides.items() if v is not None})
    _config = ServerConfig(**data)
    return _config
