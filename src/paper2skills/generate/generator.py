"""Core skill generation logic."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console

from ..providers.base import BaseLLMProvider
from .prompts import build_generation_messages

console = Console(stderr=True)


@dataclass
class GeneratedSkill:
    """A single generated skill."""

    name: str
    description: str
    body: str
    metadata: dict = field(default_factory=dict)
    source_paper: Optional[str] = None

    def to_skill_md(self) -> str:
        """Render as a complete SKILL.md file."""
        lines = ["---"]
        lines.append(f"name: {self.name}")
        lines.append(f"description: {self.description}")

        if self.metadata:
            lines.append("metadata:")
            for key, value in self.metadata.items():
                # Quote values that contain special YAML characters
                if any(c in str(value) for c in ":#{}[]|>&*!%@`"):
                    lines.append(f'  {key}: "{value}"')
                else:
                    lines.append(f"  {key}: {value}")

        lines.append("---")
        lines.append("")
        lines.append(self.body.strip())
        lines.append("")

        return "\n".join(lines)


def parse_skills_from_response(
    response: str, paper_metadata: dict
) -> list[GeneratedSkill]:
    """Parse LLM response into individual GeneratedSkill objects."""
    # Split by separator
    raw_skills = re.split(r"---SKILL_SEPARATOR---", response)

    skills = []
    for raw in raw_skills:
        raw = raw.strip()
        if not raw:
            continue

        skill = _parse_single_skill(raw, paper_metadata)
        if skill:
            skills.append(skill)

    return skills


def _parse_single_skill(raw: str, paper_metadata: dict) -> Optional[GeneratedSkill]:
    """Parse a single skill block from the LLM response."""
    # Extract frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if not fm_match:
        # Try without leading ---
        fm_match = re.match(r"^(name:.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
        if not fm_match:
            # No valid frontmatter, treat entire content as body with generated name
            console.print(
                "[yellow]  Warning: skill block missing frontmatter, skipping[/yellow]"
            )
            return None

    frontmatter_str = fm_match.group(1)
    body = fm_match.group(2).strip()

    # Parse frontmatter fields (simple YAML-like parsing)
    name = _extract_field(frontmatter_str, "name")
    description = _extract_field(frontmatter_str, "description")

    if not name or not description:
        console.print(
            "[yellow]  Warning: skill missing name or description, skipping[/yellow]"
        )
        return None

    # Validate and clean name
    name = _clean_skill_name(name)
    if not name:
        return None

    # Truncate description to 200 chars
    if len(description) > 200:
        description = description[:197] + "..."

    # Build metadata
    skill_metadata: dict = {}

    # Extract metadata block from frontmatter
    metadata_match = re.search(r"metadata:\s*\n((?:  \S.*(?:\n|$))*)", frontmatter_str)
    if metadata_match:
        for line in metadata_match.group(1).strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                skill_metadata[key.strip()] = value.strip().strip('"').strip("'")

    # Always include source paper info
    if paper_metadata.get("title"):
        skill_metadata["source-paper"] = paper_metadata["title"]
    if paper_metadata.get("arxiv_id"):
        skill_metadata["arxiv-id"] = paper_metadata["arxiv_id"]
    if paper_metadata.get("doi"):
        skill_metadata["doi"] = paper_metadata["doi"]

    return GeneratedSkill(
        name=name,
        description=description,
        body=body,
        metadata=skill_metadata,
        source_paper=paper_metadata.get("title"),
    )


def _extract_field(frontmatter: str, field_name: str) -> Optional[str]:
    """Extract a simple field value from frontmatter text."""
    pattern = rf"^{field_name}:\s*(.+)$"
    match = re.search(pattern, frontmatter, re.MULTILINE)
    if match:
        value = match.group(1).strip().strip('"').strip("'")
        return value
    return None


def _clean_skill_name(name: str) -> Optional[str]:
    """Validate and clean a skill name to match the required pattern."""
    # Remove quotes
    name = name.strip().strip('"').strip("'")
    # Lowercase
    name = name.lower()
    # Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)
    # Remove invalid characters
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Collapse consecutive hyphens
    name = re.sub(r"-{2,}", "-", name)
    # Strip leading/trailing hyphens
    name = name.strip("-")
    # Truncate to 64 chars
    if len(name) > 64:
        name = name[:64].rstrip("-")

    # Validate
    if not name or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        console.print(
            f"[yellow]  Warning: invalid skill name '{name}', skipping[/yellow]"
        )
        return None

    return name


def generate_skills(
    paper_text: str,
    metadata: dict,
    provider: BaseLLMProvider,
    max_skills: int = 5,
    audience: Optional[str] = None,
) -> list[GeneratedSkill]:
    """Generate skills from a paper using the LLM provider.

    Args:
        paper_text: Full text of the paper.
        metadata: Paper metadata dict.
        provider: LLM provider to use.
        max_skills: Maximum number of skills to extract.
        audience: Audience profile name (default: coding-agent).

    Returns a list of parsed and validated GeneratedSkill objects.
    """
    messages = build_generation_messages(paper_text, metadata, max_skills, audience)

    console.print(f"  Generating skills using [cyan]{provider.model_name}[/cyan]...")
    response = provider.chat(messages, temperature=0.3, max_tokens=4096)

    if response.usage:
        console.print(f"  Tokens used: {response.usage.get('total_tokens', 'unknown')}")

    skills = parse_skills_from_response(response.content, metadata)
    console.print(f"  Extracted [green]{len(skills)}[/green] skills")

    return skills
