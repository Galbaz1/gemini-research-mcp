"""Tests for research_document_file helpers -- URL normalization and download."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from video_research_mcp.tools.research_document_file import (
    _normalize_document_url,
    _download_document,
)


class TestNormalizeDocumentUrl:
    """Tests for _normalize_document_url."""

    def test_arxiv_abs_to_pdf(self):
        """GIVEN arxiv.org/abs URL WHEN normalized THEN converts to /pdf/.pdf."""
        result = _normalize_document_url("https://arxiv.org/abs/2401.12345")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_arxiv_abs_with_version(self):
        """GIVEN arxiv.org/abs URL with version WHEN normalized THEN preserves version."""
        result = _normalize_document_url("https://arxiv.org/abs/2401.12345v2")
        assert result == "https://arxiv.org/pdf/2401.12345v2.pdf"

    def test_arxiv_pdf_without_extension(self):
        """GIVEN arxiv.org/pdf URL without .pdf WHEN normalized THEN adds .pdf."""
        result = _normalize_document_url("https://arxiv.org/pdf/2401.12345")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_arxiv_pdf_with_version_no_extension(self):
        """GIVEN arxiv.org/pdf/XXXX.XXXXXv1 WHEN normalized THEN adds .pdf."""
        result = _normalize_document_url("https://arxiv.org/pdf/2401.12345v1")
        assert result == "https://arxiv.org/pdf/2401.12345v1.pdf"

    def test_non_arxiv_url_unchanged(self):
        """GIVEN non-arXiv URL WHEN normalized THEN returned unchanged."""
        url = "https://example.com/paper.pdf"
        assert _normalize_document_url(url) == url

    def test_http_arxiv_also_normalized(self):
        """GIVEN http:// arXiv URL WHEN normalized THEN still converts."""
        result = _normalize_document_url("http://arxiv.org/abs/2401.12345")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_arxiv_abs_trailing_slash(self):
        """GIVEN arXiv URL with trailing slash WHEN normalized THEN still converts."""
        result = _normalize_document_url("https://arxiv.org/abs/2401.12345/")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_arxiv_abs_with_query_params(self):
        """GIVEN arXiv URL with query params WHEN normalized THEN still converts."""
        result = _normalize_document_url("https://arxiv.org/abs/2401.12345?context=stat")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_arxiv_abs_trailing_slash_and_query(self):
        """GIVEN arXiv URL with trailing slash AND query WHEN normalized THEN converts."""
        result = _normalize_document_url("https://arxiv.org/abs/2401.12345v2/?utm=1")
        assert result == "https://arxiv.org/pdf/2401.12345v2.pdf"

    def test_arxiv_pdf_trailing_slash(self):
        """GIVEN arXiv /pdf/ URL with trailing slash WHEN normalized THEN adds .pdf."""
        result = _normalize_document_url("https://arxiv.org/pdf/2401.12345/")
        assert result == "https://arxiv.org/pdf/2401.12345.pdf"


class TestDownloadDocumentFilename:
    """Tests for filename extraction in _download_document."""

    async def test_unsupported_extension_preserves_original_name(self, tmp_path):
        """GIVEN URL with .docx extension WHEN downloaded THEN filename kept as-is.

        This ensures _doc_mime_type correctly rejects the unsupported extension
        downstream, rather than silently renaming to document.pdf.
        """
        mock_resp = AsyncMock()
        mock_resp.content = b"fake docx content"
        mock_resp.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("video_research_mcp.tools.research_document_file.httpx.AsyncClient", return_value=mock_client):
            result = await _download_document("https://example.com/paper.docx", tmp_path)

        assert result.name == "paper.docx"  # NOT "document.pdf"

    async def test_no_extension_defaults_to_pdf(self, tmp_path):
        """GIVEN URL with no file extension WHEN downloaded THEN defaults to document.pdf."""
        mock_resp = AsyncMock()
        mock_resp.content = b"fake pdf content"
        mock_resp.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("video_research_mcp.tools.research_document_file.httpx.AsyncClient", return_value=mock_client):
            result = await _download_document("https://example.com/document", tmp_path)

        assert result.name == "document.pdf"

    async def test_supported_extension_kept(self, tmp_path):
        """GIVEN URL with .pdf extension WHEN downloaded THEN filename preserved."""
        mock_resp = AsyncMock()
        mock_resp.content = b"fake pdf content"
        mock_resp.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("video_research_mcp.tools.research_document_file.httpx.AsyncClient", return_value=mock_client):
            result = await _download_document("https://example.com/report.pdf", tmp_path)

        assert result.name == "report.pdf"
