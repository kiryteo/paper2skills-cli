"""Plain text and markdown file ingestion."""

from __future__ import annotations

from pathlib import Path


def read_text_file(path: Path) -> tuple[str, dict]:
    """Read a plain text or markdown file.

    Returns (content, metadata) where metadata is minimal.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"File is empty: {path}")

    metadata = {
        "title": path.stem.replace("-", " ").replace("_", " ").title(),
        "source_file": str(path),
    }

    return content, metadata
