"""URL validation and safe download with SSRF protection.

Enforces HTTPS-only, blocks private/loopback/link-local IP ranges,
rejects embedded credentials, and streams downloads with a size cap.
Used by research_document to safely fetch user-supplied URLs.
"""

from __future__ import annotations

import logging
import socket
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class UrlPolicyError(Exception):
    """Raised when a URL violates the security policy."""


def validate_url(url: str) -> None:
    """Validate a URL against the security policy.

    Checks:
    - HTTPS scheme only
    - No embedded credentials (userinfo)
    - Hostname present and DNS-resolvable
    - Resolved IPs are not private, loopback, link-local, multicast, or reserved

    Raises:
        UrlPolicyError: If any check fails.
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise UrlPolicyError(f"Only HTTPS URLs are allowed, got '{parsed.scheme}://'")

    if parsed.username or parsed.password:
        raise UrlPolicyError("URLs with embedded credentials are not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UrlPolicyError("URL has no hostname")

    try:
        addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlPolicyError(f"DNS resolution failed for '{hostname}': {exc}") from exc

    for family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        ip = ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise UrlPolicyError(
                f"URL resolves to blocked IP range ({ip_str}) — "
                "private, loopback, link-local, multicast, and reserved addresses are not allowed"
            )


async def download_checked(url: str, tmp_dir: Path, *, max_bytes: int) -> Path:
    """Download a URL with SSRF protection and size limits.

    Args:
        url: HTTPS URL to download.
        tmp_dir: Directory to write the downloaded file into.
        max_bytes: Maximum response body size in bytes.

    Returns:
        Path to the downloaded file.

    Raises:
        UrlPolicyError: If the URL fails validation or the response exceeds max_bytes.
        httpx.HTTPStatusError: If the server returns an error status.
    """
    validate_url(url)

    url_path = url.rsplit("/", 1)[-1].split("?")[0]
    filename = url_path if "." in url_path else "document.pdf"
    local = tmp_dir / filename

    async with httpx.AsyncClient(follow_redirects=False, timeout=60) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            accumulated = 0
            with local.open("wb") as f:
                async for chunk in resp.aiter_bytes():
                    accumulated += len(chunk)
                    if accumulated > max_bytes:
                        raise UrlPolicyError(
                            f"Response exceeds size limit ({max_bytes} bytes)"
                        )
                    f.write(chunk)

    logger.info("Downloaded %s (%d bytes) to %s", url, accumulated, local)
    return local
