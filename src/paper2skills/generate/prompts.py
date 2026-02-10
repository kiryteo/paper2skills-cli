"""Prompt templates for skill generation."""

SYSTEM_PROMPT = """\
You are an expert at distilling research papers into actionable, concise skill \
definitions for AI coding agents. Your output must be practical instructions that \
an AI coding agent can follow — NOT academic summaries.

A "skill" is a reusable set of instructions that teaches an AI agent how to \
apply a specific technique from a research paper when coding. Skills are loaded \
on-demand: an agent sees the skill name and description, then decides whether to \
load the full content.

## Output Format

You MUST output valid YAML-delimited markdown. Each skill is separated by a line \
containing exactly `---SKILL_SEPARATOR---`. Each skill has this structure:

```
---
name: lowercase-hyphenated-name
description: One-line description (under 200 chars) that tells the agent WHEN to use this skill
metadata:
  source-paper: "Paper Title"
---

## When to use

Brief trigger conditions — when should an agent load this skill?

## Instructions

Step-by-step, actionable guidance. Use numbered steps.
Include concrete code patterns, algorithms, or formulas where applicable.

## Examples

Concrete code examples demonstrating the technique.

## Pitfalls

Common mistakes to avoid when applying this technique.
```

## Rules

1. Extract ONLY actionable coding techniques — skip background, related work, \
and pure theory that has no practical coding application.
2. Each skill must be SELF-CONTAINED — an agent reading just this skill should \
be able to apply the technique without reading the paper.
3. The `name` field must be 1-64 chars, lowercase alphanumeric with single hyphens \
(no leading/trailing hyphens, no consecutive hyphens). Regex: ^[a-z0-9]+(-[a-z0-9]+)*$
4. The `description` field must clearly state WHEN an agent should use this skill, \
not just what it does. Maximum 200 characters.
5. Keep each skill focused on ONE technique. If a paper has multiple distinct \
techniques, create multiple skills.
6. Prefer code examples over prose. Show, don't just tell.
7. If a technique is just common knowledge that any competent developer would \
know, skip it — only extract novel insights.
8. Keep total body length under 300 lines per skill.
"""

GENERATION_PROMPT = """\
Analyze the following research paper content and extract actionable coding skills.

## Paper Metadata
Title: {title}
{extra_metadata}

## Paper Content (truncated if long)
{content}

## Instructions

Extract up to {max_skills} distinct, actionable skills from this paper. \
Focus on techniques that an AI coding agent could practically apply when writing, \
reviewing, or debugging code.

If the paper contains fewer than {max_skills} actionable techniques, produce fewer \
skills. If the paper is purely theoretical with no practical coding applications, \
output a single skill with the core insight framed as guidance.

Separate each skill with a line containing exactly: ---SKILL_SEPARATOR---

Output ONLY the skills in the format specified. No preamble, no commentary.
"""


def build_generation_messages(
    paper_text: str,
    metadata: dict,
    max_skills: int = 5,
) -> list[dict[str, str]]:
    """Build the messages list for skill generation."""
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

    user_msg = GENERATION_PROMPT.format(
        title=title,
        extra_metadata=extra_metadata,
        content=content,
        max_skills=max_skills,
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
