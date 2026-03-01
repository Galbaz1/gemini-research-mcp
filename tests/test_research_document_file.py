"""Tests for research_document_file helpers -- URL normalization and download."""

from __future__ import annotations

from video_research_mcp.tools.research_document_file import _normalize_document_url


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
