"""DOI resolution and paper fetching."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import requests

from .pdf import extract_text_from_pdf

# Match DOI patterns like "10.1234/something" or full doi.org URLs
DOI_PATTERNS = [
    re.compile(r"^(10\.\d{4,9}/[^\s]+)$"),
    re.compile(r"doi\.org/(10\.\d{4,9}/[^\s]+)", re.IGNORECASE),
]


def is_doi_source(source: str) -> bool:
    """Check if a source string is a DOI reference."""
    return any(p.search(source) for p in DOI_PATTERNS)


def extract_doi(source: str) -> str:
    """Extract DOI from various input formats."""
    for pattern in DOI_PATTERNS:
        m = pattern.search(source)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract DOI from: {source}")


def fetch_doi_paper(source: str) -> tuple[str, dict]:
    """Fetch paper content via DOI resolution.

    Attempts to get the full text by:
    1. Resolving the DOI to get metadata via content negotiation
    2. Trying to download a PDF from the resolved URL
    3. Falling back to using the abstract if full text isn't available
    """
    doi = extract_doi(source)

    # Get metadata via content negotiation (Crossref JSON)
    metadata_url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/vnd.citationstyles.csl+json"}

    resp = requests.get(metadata_url, headers=headers, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    csl_data = resp.json()

    metadata = {
        "title": csl_data.get("title", "Unknown"),
        "authors": [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in csl_data.get("author", [])
        ],
        "doi": doi,
        "url": metadata_url,
        "abstract": csl_data.get("abstract", ""),
    }

    # Try to get PDF from the resolved URL
    text = None
    pdf_url = None

    # Check for PDF link in CSL data
    for link in csl_data.get("link", []):
        if link.get("content-type") == "application/pdf":
            pdf_url = link.get("URL")
            break

    if pdf_url:
        try:
            pdf_resp = requests.get(pdf_url, timeout=60)
            pdf_resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_resp.content)
                tmp_path = Path(tmp.name)
            text = extract_text_from_pdf(tmp_path)
            tmp_path.unlink()
        except Exception:
            text = None

    if text is None:
        # Fall back to abstract
        abstract = metadata.get("abstract", "")
        if abstract:
            text = f"Title: {metadata['title']}\n\nAbstract:\n{abstract}"
        else:
            raise ValueError(
                f"Could not retrieve full text or abstract for DOI: {doi}. "
                "Try downloading the PDF manually and using the local PDF input."
            )

    return text, metadata
