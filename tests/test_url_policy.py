"""Tests for URL policy validation and safe download."""

from __future__ import annotations

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_research_mcp.url_policy import UrlPolicyError, download_checked, validate_url


def _mock_getaddrinfo(ip: str):
    """Return a mock getaddrinfo result resolving to the given IP."""
    return [(2, 1, 6, "", (ip, 0))]


class _AsyncIterBytes:
    """Async iterator that yields chunks of bytes."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = iter(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._chunks)
        except StopIteration:
            raise StopAsyncIteration


class _FakeResponse:
    """Minimal httpx response mock with async streaming."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def raise_for_status(self):
        pass

    def aiter_bytes(self):
        return _AsyncIterBytes(self._chunks)


class _FakeStreamCtx:
    """Async context manager wrapping a FakeResponse."""

    def __init__(self, resp: _FakeResponse):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *args):
        pass


class _FakeClient:
    """Minimal httpx.AsyncClient mock."""

    def __init__(self, resp: _FakeResponse):
        self._resp = resp

    def stream(self, method, url):
        return _FakeStreamCtx(self._resp)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class TestValidateUrl:
    """Tests for validate_url()."""

    def test_rejects_http(self):
        """HTTP scheme is blocked — only HTTPS allowed."""
        with pytest.raises(UrlPolicyError, match="Only HTTPS"):
            validate_url("http://example.com/doc.pdf")

    def test_rejects_ftp(self):
        """FTP scheme is blocked."""
        with pytest.raises(UrlPolicyError, match="Only HTTPS"):
            validate_url("ftp://example.com/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", return_value=_mock_getaddrinfo("93.184.216.34"))
    def test_accepts_https(self, _mock_dns):
        """HTTPS with a public IP passes."""
        validate_url("https://example.com/doc.pdf")

    def test_rejects_credentials(self):
        """URLs with embedded user:pass are blocked."""
        with pytest.raises(UrlPolicyError, match="embedded credentials"):
            validate_url("https://user:pass@example.com/doc.pdf")

    def test_rejects_username_only(self):
        """URLs with embedded username (no password) are blocked."""
        with pytest.raises(UrlPolicyError, match="embedded credentials"):
            validate_url("https://user@example.com/doc.pdf")

    def test_rejects_no_hostname(self):
        """URLs without a hostname are blocked."""
        with pytest.raises(UrlPolicyError, match="no hostname"):
            validate_url("https:///path/to/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", return_value=_mock_getaddrinfo("192.168.1.1"))
    def test_rejects_private_ip(self, _mock_dns):
        """Private IPs (192.168.x.x) are blocked."""
        with pytest.raises(UrlPolicyError, match="blocked IP range"):
            validate_url("https://internal.corp/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", return_value=_mock_getaddrinfo("10.0.0.1"))
    def test_rejects_private_10_range(self, _mock_dns):
        """Private IPs (10.x.x.x) are blocked."""
        with pytest.raises(UrlPolicyError, match="blocked IP range"):
            validate_url("https://internal.corp/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", return_value=_mock_getaddrinfo("127.0.0.1"))
    def test_rejects_loopback(self, _mock_dns):
        """Loopback (127.0.0.1) is blocked."""
        with pytest.raises(UrlPolicyError, match="blocked IP range"):
            validate_url("https://localhost/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", return_value=_mock_getaddrinfo("169.254.169.254"))
    def test_rejects_link_local(self, _mock_dns):
        """Link-local (169.254.x.x, cloud metadata) is blocked."""
        with pytest.raises(UrlPolicyError, match="blocked IP range"):
            validate_url("https://metadata.google.internal/doc.pdf")

    @patch("video_research_mcp.url_policy.socket.getaddrinfo", side_effect=socket.gaierror("Name resolution failed"))
    def test_rejects_dns_failure(self, _mock_dns):
        """DNS resolution failure is blocked."""
        with pytest.raises(UrlPolicyError, match="DNS resolution failed"):
            validate_url("https://nonexistent.example.invalid/doc.pdf")


class TestDownloadChecked:
    """Tests for download_checked()."""

    async def test_enforces_size_limit(self, tmp_path: Path):
        """Downloads exceeding max_bytes raise UrlPolicyError."""
        large_chunk = b"x" * 1000
        resp = _FakeResponse([large_chunk, large_chunk])
        client = _FakeClient(resp)

        with (
            patch("video_research_mcp.url_policy.validate_url"),
            patch("video_research_mcp.url_policy.httpx.AsyncClient", return_value=client),
        ):
            with pytest.raises(UrlPolicyError, match="exceeds size limit"):
                await download_checked(
                    "https://example.com/huge.pdf", tmp_path, max_bytes=500
                )

    async def test_no_redirects(self, tmp_path: Path):
        """Client is created with follow_redirects=False."""
        resp = _FakeResponse([b"content"])
        client = _FakeClient(resp)
        mock_cls = MagicMock(return_value=client)

        with (
            patch("video_research_mcp.url_policy.validate_url"),
            patch("video_research_mcp.url_policy.httpx.AsyncClient", mock_cls),
        ):
            await download_checked(
                "https://example.com/doc.pdf", tmp_path, max_bytes=10_000
            )
            mock_cls.assert_called_once_with(follow_redirects=False, timeout=60)

    async def test_writes_file(self, tmp_path: Path):
        """Happy path: file is written to tmp_dir."""
        content = b"PDF content here"
        resp = _FakeResponse([content])
        client = _FakeClient(resp)

        with (
            patch("video_research_mcp.url_policy.validate_url"),
            patch("video_research_mcp.url_policy.httpx.AsyncClient", return_value=client),
        ):
            result = await download_checked(
                "https://example.com/report.pdf", tmp_path, max_bytes=10_000
            )

        assert result == tmp_path / "report.pdf"
        assert result.read_bytes() == content

    async def test_fallback_filename(self, tmp_path: Path):
        """URLs without a file extension use document.pdf as filename."""
        resp = _FakeResponse([b"data"])
        client = _FakeClient(resp)

        with (
            patch("video_research_mcp.url_policy.validate_url"),
            patch("video_research_mcp.url_policy.httpx.AsyncClient", return_value=client),
        ):
            result = await download_checked(
                "https://example.com/download", tmp_path, max_bytes=10_000
            )

        assert result.name == "document.pdf"
