"""Tests for source type detection and arXiv ID extraction."""

import pytest

from paper2skills.ingest.router import detect_source_type
from paper2skills.ingest.arxiv_fetch import is_arxiv_source, extract_arxiv_id
from paper2skills.ingest.doi import is_doi_source


# ---------------------------------------------------------------------------
# detect_source_type
# ---------------------------------------------------------------------------


class TestDetectSourceType:
    # arXiv variants
    def test_arxiv_prefix(self):
        assert detect_source_type("arxiv:1706.03762") == "arxiv"

    def test_arxiv_prefix_uppercase(self):
        assert detect_source_type("arXiv:1706.03762") == "arxiv"

    def test_arxiv_bare_id(self):
        assert detect_source_type("1706.03762") == "arxiv"

    def test_arxiv_url_abs(self):
        assert detect_source_type("https://arxiv.org/abs/1706.03762") == "arxiv"

    def test_arxiv_url_pdf(self):
        assert detect_source_type("https://arxiv.org/pdf/1706.03762") == "arxiv"

    def test_arxiv_with_version(self):
        assert detect_source_type("arxiv:1706.03762v2") == "arxiv"

    # DOI variants
    def test_doi_bare(self):
        assert detect_source_type("10.1038/s41586-021-03819-2") == "doi"

    def test_doi_url(self):
        assert detect_source_type("https://doi.org/10.1038/s41586-021-03819-2") == "doi"

    # File types
    def test_pdf_path(self):
        assert detect_source_type("paper.pdf") == "pdf"

    def test_pdf_path_with_dir(self):
        assert detect_source_type("/some/path/paper.pdf") == "pdf"

    def test_txt_file(self):
        assert detect_source_type("notes.txt") == "text"

    def test_md_file(self):
        assert detect_source_type("paper.md") == "text"

    def test_markdown_file(self):
        assert detect_source_type("paper.markdown") == "text"

    # URL detection
    def test_https_url(self):
        assert detect_source_type("https://example.com/paper.html") == "url"

    def test_http_url(self):
        assert detect_source_type("http://example.com/paper.html") == "url"

    # Unknown
    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Cannot determine source type"):
            detect_source_type("some-random-string-that-is-not-a-source")


# ---------------------------------------------------------------------------
# is_arxiv_source / extract_arxiv_id
# ---------------------------------------------------------------------------


class TestArxivHelpers:
    def test_is_arxiv_with_prefix(self):
        assert is_arxiv_source("arxiv:2401.12345") is True

    def test_is_arxiv_bare_id(self):
        assert is_arxiv_source("2401.12345") is True

    def test_is_arxiv_url(self):
        assert is_arxiv_source("https://arxiv.org/abs/2401.12345v3") is True

    def test_is_not_arxiv(self):
        assert is_arxiv_source("10.1038/s41586") is False

    def test_extract_from_prefix(self):
        assert extract_arxiv_id("arxiv:1706.03762") == "1706.03762"

    def test_extract_from_bare(self):
        assert extract_arxiv_id("2401.12345") == "2401.12345"

    def test_extract_from_url(self):
        assert extract_arxiv_id("https://arxiv.org/abs/2401.12345v2") == "2401.12345v2"

    def test_extract_invalid_raises(self):
        with pytest.raises(ValueError, match="Could not extract arXiv ID"):
            extract_arxiv_id("not-an-arxiv-id")


# ---------------------------------------------------------------------------
# is_doi_source
# ---------------------------------------------------------------------------


class TestDoiHelpers:
    def test_is_doi_bare(self):
        assert is_doi_source("10.1038/s41586-021-03819-2") is True

    def test_is_doi_url(self):
        assert is_doi_source("https://doi.org/10.1038/s41586-021-03819-2") is True

    def test_is_not_doi(self):
        assert is_doi_source("arxiv:1706.03762") is False
