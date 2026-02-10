"""Tests for enhanced DOI support (Semantic Scholar + Unpaywall)."""

from unittest.mock import patch, MagicMock

import pytest

from paper2skills.ingest.doi import (
    fetch_semantic_scholar,
    fetch_unpaywall,
    _download_pdf_text,
    _fetch_crossref_metadata,
    UNPAYWALL_EMAIL,
)


class TestFetchSemanticScholar:
    def test_returns_metadata_and_pdf(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Test Paper",
            "abstract": "An abstract.",
            "authors": [{"name": "Alice"}, {"name": "Bob"}],
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = fetch_semantic_scholar("10.1234/test")

        assert meta["title"] == "Test Paper"
        assert meta["abstract"] == "An abstract."
        assert meta["authors"] == ["Alice", "Bob"]
        assert pdf_url == "https://example.com/paper.pdf"

    def test_returns_none_on_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = fetch_semantic_scholar("10.1234/missing")

        assert meta is None
        assert pdf_url is None

    def test_returns_none_on_network_error(self):
        with patch(
            "paper2skills.ingest.doi.requests.get",
            side_effect=Exception("timeout"),
        ):
            meta, pdf_url = fetch_semantic_scholar("10.1234/error")

        assert meta is None
        assert pdf_url is None

    def test_no_open_access_pdf(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Closed Paper",
            "authors": [],
            "openAccessPdf": None,
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = fetch_semantic_scholar("10.1234/closed")

        assert meta is not None
        assert meta["title"] == "Closed Paper"
        assert pdf_url is None

    def test_partial_metadata(self):
        """Only title returned, no abstract or authors."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Partial Paper",
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = fetch_semantic_scholar("10.1234/partial")

        assert meta is not None
        assert meta["title"] == "Partial Paper"
        assert pdf_url is None


class TestFetchUnpaywall:
    def test_returns_pdf_url_from_best_oa(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "best_oa_location": {
                "url_for_pdf": "https://example.com/oa.pdf",
            },
            "oa_locations": [],
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            url = fetch_unpaywall("10.1234/test")

        assert url == "https://example.com/oa.pdf"

    def test_falls_back_to_landing_page(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "best_oa_location": {
                "url_for_pdf": None,
                "url_for_landing_page": "https://example.com/landing",
            },
            "oa_locations": [],
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            url = fetch_unpaywall("10.1234/test")

        assert url == "https://example.com/landing"

    def test_falls_back_to_oa_locations(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "best_oa_location": None,
            "oa_locations": [
                {"url_for_pdf": "https://example.com/alt.pdf"},
            ],
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            url = fetch_unpaywall("10.1234/test")

        assert url == "https://example.com/alt.pdf"

    def test_returns_none_on_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            url = fetch_unpaywall("10.1234/missing")

        assert url is None

    def test_returns_none_on_network_error(self):
        with patch(
            "paper2skills.ingest.doi.requests.get",
            side_effect=Exception("timeout"),
        ):
            url = fetch_unpaywall("10.1234/error")

        assert url is None

    def test_returns_none_when_no_oa(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "best_oa_location": None,
            "oa_locations": [],
        }

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            url = fetch_unpaywall("10.1234/closed")

        assert url is None

    def test_uses_provided_email(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"best_oa_location": None, "oa_locations": []}

        with patch(
            "paper2skills.ingest.doi.requests.get", return_value=mock_resp
        ) as mock_get:
            fetch_unpaywall("10.1234/test", email="me@example.com")
            call_url = mock_get.call_args[0][0]
            assert "email=me@example.com" in call_url


class TestDownloadPdfText:
    def test_returns_none_on_non_pdf_content_type(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            result = _download_pdf_text("https://example.com/page.html")

        assert result is None

    def test_returns_none_on_network_error(self):
        with patch(
            "paper2skills.ingest.doi.requests.get",
            side_effect=Exception("connection error"),
        ):
            result = _download_pdf_text("https://example.com/broken.pdf")

        assert result is None


class TestFetchCrossrefMetadata:
    def test_parses_csl_json(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Crossref Paper",
            "author": [
                {"given": "Jane", "family": "Doe"},
                {"given": "John", "family": "Smith"},
            ],
            "abstract": "Some abstract text.",
            "link": [
                {
                    "content-type": "application/pdf",
                    "URL": "https://example.com/cr.pdf",
                },
            ],
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = _fetch_crossref_metadata("10.1234/test")

        assert meta["title"] == "Crossref Paper"
        assert meta["authors"] == ["Jane Doe", "John Smith"]
        assert meta["abstract"] == "Some abstract text."
        assert meta["doi"] == "10.1234/test"
        assert pdf_url == "https://example.com/cr.pdf"

    def test_no_pdf_link(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "No PDF Paper",
            "author": [],
            "link": [],
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("paper2skills.ingest.doi.requests.get", return_value=mock_resp):
            meta, pdf_url = _fetch_crossref_metadata("10.1234/nopdf")

        assert meta["title"] == "No PDF Paper"
        assert pdf_url is None
