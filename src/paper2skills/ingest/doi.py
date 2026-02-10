"""DOI resolution and paper fetching.

Fallback chain for full-text retrieval:
  1. Crossref content negotiation (CSL-JSON metadata + PDF link)
  2. Semantic Scholar API (metadata + open-access PDF)
  3. Unpaywall API (open-access PDF discovery)
  4. Abstract-only fallback
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console

from .pdf import extract_text_from_pdf

console = Console(stderr=True)

# Match DOI patterns like "10.1234/something" or full doi.org URLs
DOI_PATTERNS = [
    re.compile(r"^(10\.\d{4,9}/[^\s]+)$"),
    re.compile(r"doi\.org/(10\.\d{4,9}/[^\s]+)", re.IGNORECASE),
]

# Unpaywall requires an email for polite usage
UNPAYWALL_EMAIL = "paper2skills@users.noreply.github.com"


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


# ---------------------------------------------------------------------------
# PDF download helper
# ---------------------------------------------------------------------------


def _download_pdf_text(pdf_url: str) -> Optional[str]:
    """Download a PDF from a URL and extract text. Returns None on failure."""
    try:
        pdf_resp = requests.get(pdf_url, timeout=60)
        pdf_resp.raise_for_status()

        content_type = pdf_resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not pdf_url.lower().endswith(".pdf"):
            return None

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_resp.content)
            tmp_path = Path(tmp.name)
        try:
            text = extract_text_from_pdf(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        return text if text and text.strip() else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------


def _fetch_crossref_metadata(doi: str) -> tuple[dict, Optional[str]]:
    """Fetch metadata and optional PDF URL from Crossref via DOI content negotiation.

    Returns (metadata_dict, pdf_url_or_None).
    """
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

    # Look for PDF link in CSL data
    pdf_url = None
    for link in csl_data.get("link", []):
        if link.get("content-type") == "application/pdf":
            pdf_url = link.get("URL")
            break

    return metadata, pdf_url


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------


def fetch_semantic_scholar(doi: str) -> tuple[Optional[dict], Optional[str]]:
    """Query Semantic Scholar API for paper metadata and open-access PDF URL.

    Returns (extra_metadata_or_None, pdf_url_or_None).
    """
    api_url = (
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
        f"?fields=title,authors,abstract,openAccessPdf,externalIds"
    )

    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code != 200:
            return None, None

        data = resp.json()

        extra_meta: dict = {}
        if data.get("title"):
            extra_meta["title"] = data["title"]
        if data.get("abstract"):
            extra_meta["abstract"] = data["abstract"]
        if data.get("authors"):
            extra_meta["authors"] = [a.get("name", "") for a in data["authors"]]

        pdf_url = None
        oa = data.get("openAccessPdf")
        if oa and oa.get("url"):
            pdf_url = oa["url"]

        return extra_meta or None, pdf_url
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Unpaywall
# ---------------------------------------------------------------------------


def fetch_unpaywall(doi: str, email: str = UNPAYWALL_EMAIL) -> Optional[str]:
    """Query Unpaywall API for an open-access PDF URL.

    Returns pdf_url or None.
    """
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"

    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code != 200:
            return None

        data = resp.json()

        # Check best OA location first
        best_oa = data.get("best_oa_location")
        if best_oa:
            pdf_url = best_oa.get("url_for_pdf")
            if pdf_url:
                return pdf_url
            # Some locations have url_for_landing_page but not pdf
            landing = best_oa.get("url_for_landing_page")
            if landing:
                return landing

        # Check all OA locations
        for loc in data.get("oa_locations", []):
            pdf_url = loc.get("url_for_pdf")
            if pdf_url:
                return pdf_url

        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def fetch_doi_paper(source: str) -> tuple[str, dict]:
    """Fetch paper content via DOI resolution.

    Fallback chain:
    1. Crossref metadata + PDF link
    2. Semantic Scholar open-access PDF
    3. Unpaywall open-access PDF
    4. Abstract-only (from Crossref or Semantic Scholar)
    """
    doi = extract_doi(source)

    # Step 1: Crossref (always — we need the metadata)
    console.print(f"  Querying Crossref for DOI: [cyan]{doi}[/cyan]")
    metadata, crossref_pdf_url = _fetch_crossref_metadata(doi)

    text = None

    # Try Crossref PDF
    if crossref_pdf_url:
        console.print(f"  Trying Crossref PDF link...")
        text = _download_pdf_text(crossref_pdf_url)

    # Step 2: Semantic Scholar
    if text is None:
        console.print(f"  Querying Semantic Scholar...")
        s2_meta, s2_pdf_url = fetch_semantic_scholar(doi)

        # Merge any extra metadata
        if s2_meta:
            if not metadata.get("abstract") and s2_meta.get("abstract"):
                metadata["abstract"] = s2_meta["abstract"]
            if metadata.get("title") == "Unknown" and s2_meta.get("title"):
                metadata["title"] = s2_meta["title"]
            if not metadata.get("authors") and s2_meta.get("authors"):
                metadata["authors"] = s2_meta["authors"]

        if s2_pdf_url:
            console.print(f"  Trying Semantic Scholar open-access PDF...")
            text = _download_pdf_text(s2_pdf_url)

    # Step 3: Unpaywall
    if text is None:
        console.print(f"  Querying Unpaywall...")
        unpaywall_url = fetch_unpaywall(doi)
        if unpaywall_url:
            console.print(f"  Trying Unpaywall open-access PDF...")
            text = _download_pdf_text(unpaywall_url)

    # Step 4: Abstract fallback
    if text is None:
        abstract = metadata.get("abstract", "")
        if abstract:
            console.print(
                f"  [yellow]No full text available, using abstract only[/yellow]"
            )
            text = f"Title: {metadata['title']}\n\nAbstract:\n{abstract}"
        else:
            raise ValueError(
                f"Could not retrieve full text or abstract for DOI: {doi}. "
                "Try downloading the PDF manually and using the local PDF input."
            )

    return text, metadata
