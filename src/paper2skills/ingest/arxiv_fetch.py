"""arXiv paper fetching and extraction."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Optional

import arxiv

from .pdf import extract_text_from_pdf


# Match patterns like "arxiv:2401.12345", "2401.12345", or full arXiv URLs
ARXIV_PATTERNS = [
    re.compile(r"^arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)$", re.IGNORECASE),
    re.compile(r"^(\d{4}\.\d{4,5}(?:v\d+)?)$"),
    re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE),
]


def is_arxiv_source(source: str) -> bool:
    """Check if a source string is an arXiv reference."""
    return any(p.search(source) for p in ARXIV_PATTERNS)


def extract_arxiv_id(source: str) -> str:
    """Extract the arXiv ID from various input formats."""
    for pattern in ARXIV_PATTERNS:
        m = pattern.search(source)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract arXiv ID from: {source}")


def fetch_arxiv_paper(source: str) -> tuple[str, dict]:
    """Fetch an arXiv paper and return (text_content, metadata).

    Downloads the PDF and extracts text, also returns metadata
    (title, authors, abstract, etc.).
    """
    arxiv_id = extract_arxiv_id(source)

    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(client.results(search))

    if not results:
        raise ValueError(f"No arXiv paper found for ID: {arxiv_id}")

    paper = results[0]

    metadata = {
        "title": paper.title,
        "authors": [str(a) for a in paper.authors],
        "abstract": paper.summary,
        "arxiv_id": arxiv_id,
        "published": str(paper.published.date()) if paper.published else None,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }

    # Download PDF to temp directory and extract text
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = paper.download_pdf(dirpath=tmpdir)
        text = extract_text_from_pdf(Path(pdf_path))

    return text, metadata
