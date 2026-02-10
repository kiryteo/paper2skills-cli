"""Markdown output formatter — flat single-file output."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..generate.generator import GeneratedSkill
from .base import BaseOutputFormatter

console = Console(stderr=True)


class MarkdownFormatter(BaseOutputFormatter):
    """Writes all skills into a single Markdown file."""

    @property
    def format_name(self) -> str:
        return "markdown"

    @property
    def file_extension(self) -> str:
        return ".md"

    def format_skill(self, skill: GeneratedSkill) -> str:
        """Format a single skill as a Markdown section."""
        lines: list[str] = []
        lines.append(f"## {skill.name}")
        lines.append("")
        lines.append(f"**{skill.description}**")
        lines.append("")

        if skill.metadata:
            lines.append("| Key | Value |")
            lines.append("|-----|-------|")
            for key, value in skill.metadata.items():
                lines.append(f"| {key} | {value} |")
            lines.append("")

        lines.append(skill.body.strip())
        lines.append("")

        return "\n".join(lines)

    def format_all(self, skills: list[GeneratedSkill]) -> str:
        """Format all skills as a single Markdown document."""
        lines: list[str] = []
        lines.append("# Generated Skills")
        lines.append("")
        lines.append(f"Total: {len(skills)} skills")
        lines.append("")

        for i, skill in enumerate(skills):
            if i > 0:
                lines.append("---")
                lines.append("")
            lines.append(self.format_skill(skill))

        return "\n".join(lines)

    def write_skills(
        self,
        skills: list[GeneratedSkill],
        output_dir: Path,
    ) -> list[Path]:
        """Write all skills as a single Markdown file.

        Creates: output_dir/skills.md
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "skills.md"

        content = self.format_all(skills)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"  Wrote: [green]{out_path}[/green] ({len(skills)} skills)")

        return [out_path]
