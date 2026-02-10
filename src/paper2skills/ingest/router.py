"""Unified paper ingestion router.

Detects source type and dispatches to the appropriate ingester.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from .arxiv_fetch import is_arxiv_source, fetch_arxiv_paper
from .doi import is_doi_source, fetch_doi_paper
from .pdf import extract_text_from_pdf
from .text import read_text_file

console = Console(stderr=True)


def detect_source_type(source: str) -> str:
    """Detect the type of paper source from a string.

    Returns one of: 'arxiv', 'doi', 'pdf', 'text', 'url'
    """
    if is_arxiv_source(source):
        return "arxiv"
    if is_doi_source(source):
        return "doi"

    path = Path(source)
    if path.suffix.lower() == ".pdf":
        return "pdf"
    if path.suffix.lower() in (".md", ".txt", ".markdown"):
        return "text"
    if source.startswith("http://") or source.startswith("https://"):
        return "url"

    # If it's a file that exists, treat as text
    if path.exists():
        return "text"

    raise ValueError(
        f"Cannot determine source type for: {source}\n"
        "Supported formats: local PDF, arXiv ID/URL, DOI, text/markdown file"
    )


def ingest_paper(source: str) -> tuple[str, dict]:
    """Ingest a paper from any supported source.

    Returns (text_content, metadata) where metadata includes
    title, authors, and source-specific fields.
    """
    source_type = detect_source_type(source)
    console.print(f"  Detected source type: [cyan]{source_type}[/cyan]")

    if source_type == "arxiv":
        console.print(f"  Fetching from arXiv...")
        return fetch_arxiv_paper(source)

    elif source_type == "doi":
        console.print(f"  Resolving DOI...")
        return fetch_doi_paper(source)

    elif source_type == "pdf":
        path = Path(source)
        console.print(f"  Extracting text from PDF...")
        text = extract_text_from_pdf(path)
        metadata = {
            "title": path.stem.replace("-", " ").replace("_", " ").title(),
            "source_file": str(path),
        }
        return text, metadata

    elif source_type == "text":
        path = Path(source)
        console.print(f"  Reading text file...")
        return read_text_file(path)

    elif source_type == "url":
        # For generic URLs, try to download as PDF
        console.print(f"  Downloading from URL...")
        return _fetch_url_as_pdf(source)

    else:
        raise ValueError(f"Unsupported source type: {source_type}")


def _fetch_url_as_pdf(url: str) -> tuple[str, dict]:
    """Try to download a URL as PDF and extract text."""
    import tempfile
    import requests

    resp = requests.get(url, timeout=60, allow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")

    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = Path(tmp.name)
        try:
            text = extract_text_from_pdf(tmp_path)
        finally:
            tmp_path.unlink()

        metadata = {"title": "Unknown", "url": url}
        return text, metadata
    else:
        # Treat as plain text / HTML
        text = resp.text
        if not text.strip():
            raise ValueError(f"No content could be extracted from URL: {url}")
        metadata = {"title": "Unknown", "url": url}
        return text, metadata
