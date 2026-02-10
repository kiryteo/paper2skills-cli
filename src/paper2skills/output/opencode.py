"""OpenCode SKILL.md output writer."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..generate.generator import GeneratedSkill

console = Console(stderr=True)


def write_skills(
    skills: list[GeneratedSkill],
    output_dir: Path,
) -> list[Path]:
    """Write generated skills as OpenCode SKILL.md files.

    Creates the directory structure:
      output_dir/<skill-name>/SKILL.md

    Returns list of paths to written files.
    """
    written: list[Path] = []

    for skill in skills:
        skill_dir = output_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"
        content = skill.to_skill_md()

        skill_path.write_text(content, encoding="utf-8")
        written.append(skill_path)

        console.print(f"  Wrote: [green]{skill_path}[/green]")

    return written


def read_existing_skills(skills_dir: Path) -> list[GeneratedSkill]:
    """Read existing SKILL.md files from a directory.

    Parses the frontmatter and body of each SKILL.md file.
    """
    import re

    skills: list[GeneratedSkill] = []

    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_path = skill_dir / "SKILL.md"
        if not skill_path.exists():
            continue

        content = skill_path.read_text(encoding="utf-8")

        # Parse frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not fm_match:
            continue

        frontmatter = fm_match.group(1)
        body = fm_match.group(2).strip()

        # Extract fields
        name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)

        if not name_match or not desc_match:
            continue

        name = name_match.group(1).strip().strip('"').strip("'")
        description = desc_match.group(1).strip().strip('"').strip("'")

        # Extract metadata
        metadata: dict = {}
        meta_match = re.search(r"metadata:\s*\n((?:  \S.*(?:\n|$))*)", frontmatter)
        if meta_match:
            for line in meta_match.group(1).strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip().strip('"').strip("'")

        skills.append(
            GeneratedSkill(
                name=name,
                description=description,
                body=body,
                metadata=metadata,
                source_paper=metadata.get("source-paper"),
            )
        )

    return skills
