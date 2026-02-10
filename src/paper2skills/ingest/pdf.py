"""PDF text extraction using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz  # pymupdf


def extract_text_from_pdf(path: Path) -> str:
    """Extract text content from a PDF file.

    Preserves page structure and attempts to maintain reading order.
    """
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(str(path))
    pages: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append(text)

    doc.close()

    if not pages:
        raise ValueError(f"No text could be extracted from: {path}")

    return "\n\n".join(pages)
