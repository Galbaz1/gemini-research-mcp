"""Structured error handling — error categories, classification, and tool error model."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ErrorCategory(str, Enum):
    """Categories of errors for diagnostics."""

    URL_INVALID = "URL_INVALID"
    URL_PARSE_FAILED = "URL_PARSE_FAILED"
    API_PERMISSION_DENIED = "API_PERMISSION_DENIED"
    API_QUOTA_EXCEEDED = "API_QUOTA_EXCEEDED"
    API_INVALID_ARGUMENT = "API_INVALID_ARGUMENT"
    API_NOT_FOUND = "API_NOT_FOUND"
    VIDEO_RESTRICTED = "VIDEO_RESTRICTED"
    VIDEO_PRIVATE = "VIDEO_PRIVATE"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


class ToolError(BaseModel):
    """Structured error returned from any tool."""

    error: str
    category: str
    hint: str
    retryable: bool = False
    retry_after_seconds: int | None = None


def categorize_error(error: Exception) -> tuple[ErrorCategory, str]:
    """Map an exception to an ErrorCategory + human-readable hint."""
    s = str(error).lower()

    if "403" in s and "permission" in s:
        return (
            ErrorCategory.API_PERMISSION_DENIED,
            "API key lacks permission OR video is restricted (age-gated, region-locked, private)",
        )
    if "403" in s:
        return (
            ErrorCategory.VIDEO_RESTRICTED,
            "Video access denied — likely age-restricted, region-locked, or login required",
        )
    if "429" in s or "quota" in s or "resource_exhausted" in s:
        return (
            ErrorCategory.API_QUOTA_EXCEEDED,
            "API quota exceeded — wait a minute or upgrade plan",
        )
    if "400" in s and "mime" in s:
        return (
            ErrorCategory.API_INVALID_ARGUMENT,
            "Invalid URL format or resource returned HTML instead of expected data",
        )
    if "400" in s:
        return (
            ErrorCategory.API_INVALID_ARGUMENT,
            "Bad request — check input format",
        )
    if "invalid mode" in s or "invalid thinking level" in s:
        return (
            ErrorCategory.API_INVALID_ARGUMENT,
            "Invalid input parameter — check mode and thinking level values",
        )
    if "404" in s:
        return (
            ErrorCategory.VIDEO_UNAVAILABLE,
            "Resource not found — deleted or invalid ID",
        )
    if "private" in s:
        return (
            ErrorCategory.VIDEO_PRIVATE,
            "Resource is private — requires authentication",
        )
    if "unavailable" in s:
        return (
            ErrorCategory.VIDEO_UNAVAILABLE,
            "Resource unavailable in your region or deleted",
        )
    if "timeout" in s or "timed out" in s:
        return (
            ErrorCategory.NETWORK_ERROR,
            "Request timed out — try again or check connectivity",
        )

    return (ErrorCategory.UNKNOWN, str(error))


def make_tool_error(error: Exception) -> dict:
    """Create a serialisable ToolError dict from an exception."""
    cat, hint = categorize_error(error)
    retryable = cat in {
        ErrorCategory.API_QUOTA_EXCEEDED,
        ErrorCategory.NETWORK_ERROR,
    }
    return ToolError(
        error=str(error),
        category=cat.value,
        hint=hint,
        retryable=retryable,
        retry_after_seconds=60 if cat == ErrorCategory.API_QUOTA_EXCEEDED else None,
    ).model_dump()
