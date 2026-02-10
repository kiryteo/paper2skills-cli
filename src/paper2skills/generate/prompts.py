"""Prompt templates for skill generation."""

from __future__ import annotations

from typing import Optional

from ..profiles import AudienceProfile, get_profile, DEFAULT_AUDIENCE

# ---------------------------------------------------------------------------
# System prompt — assembled from profile fragments
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """\
You are an expert at distilling research papers into actionable, concise skill \
definitions for {audience_label}. Your output must be practical instructions that \
{audience_preposition} can follow — NOT academic summaries.

{skill_definition}

## Output Format

You MUST output valid YAML-delimited markdown. Each skill is separated by a line \
containing exactly `---SKILL_SEPARATOR---`. Each skill has this structure:

```
---
name: lowercase-hyphenated-name
description: One-line description (under 200 chars) that tells the reader WHEN to use this skill
metadata:
  source-paper: "Paper Title"
---

{output_section_headings}
```

## Rules

1. {extraction_focus}
2. The `name` field must be 1-64 chars, lowercase alphanumeric with single hyphens \
(no leading/trailing hyphens, no consecutive hyphens). Regex: ^[a-z0-9]+(-[a-z0-9]+)*$
3. The `description` field must clearly state WHEN to use this skill, \
not just what it does. Maximum 200 characters.
4. Keep each skill focused on ONE technique. If a paper has multiple distinct \
techniques, create multiple skills.
{rules}
"""

_USER_TEMPLATE = """\
Analyze the following research paper content and extract actionable skills.

## Paper Metadata
Title: {title}
{extra_metadata}

## Paper Content (truncated if long)
{content}

## Instructions

Extract up to {max_skills} distinct, actionable skills from this paper. \
{extraction_focus}

If the paper contains fewer than {max_skills} actionable techniques, produce fewer \
skills. If the paper is purely theoretical with no practical applications, \
output a single skill with the core insight framed as guidance.

Separate each skill with a line containing exactly: ---SKILL_SEPARATOR---

Output ONLY the skills in the format specified. No preamble, no commentary.
"""

# Pre-built audience prepositions for natural phrasing
_AUDIENCE_PREPOSITIONS = {
    "coding-agent": "an AI coding agent",
    "researcher": "a researcher",
    "general": "a reader",
}


def _build_system_prompt(profile: AudienceProfile) -> str:
    """Build the system prompt from a profile."""
    return _SYSTEM_TEMPLATE.format(
        audience_label=profile.label,
        audience_preposition=_AUDIENCE_PREPOSITIONS.get(profile.name, "the reader"),
        skill_definition=profile.skill_definition,
        output_section_headings=profile.output_section_headings,
        extraction_focus=profile.extraction_focus,
        rules=profile.rules,
    )


def build_generation_messages(
    paper_text: str,
    metadata: dict,
    max_skills: int = 5,
    audience: Optional[str] = None,
) -> list[dict[str, str]]:
    """Build the messages list for skill generation.

    Args:
        paper_text: Full text of the paper.
        metadata: Paper metadata dict (title, authors, arxiv_id, doi, abstract).
        max_skills: Maximum number of skills to extract.
        audience: Audience profile name (default: coding-agent).
    """
    profile = get_profile(audience or DEFAULT_AUDIENCE)
    title = metadata.get("title", "Unknown")

    extra_parts = []
    if metadata.get("authors"):
        authors = metadata["authors"]
        if isinstance(authors, list):
            authors = ", ".join(authors)
        extra_parts.append(f"Authors: {authors}")
    if metadata.get("arxiv_id"):
        extra_parts.append(f"arXiv: {metadata['arxiv_id']}")
    if metadata.get("doi"):
        extra_parts.append(f"DOI: {metadata['doi']}")
    if metadata.get("abstract"):
        extra_parts.append(f"Abstract: {metadata['abstract']}")

    extra_metadata = "\n".join(extra_parts)

    # Truncate paper content to ~60k chars to stay within context limits
    content = paper_text
    if len(content) > 60000:
        content = content[:60000] + "\n\n[... content truncated ...]"

    system_prompt = _build_system_prompt(profile)

    user_msg = _USER_TEMPLATE.format(
        title=title,
        extra_metadata=extra_metadata,
        content=content,
        max_skills=max_skills,
        extraction_focus=profile.extraction_focus,
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
