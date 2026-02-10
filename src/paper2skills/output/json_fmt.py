"""JSON output formatter."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from ..generate.generator import GeneratedSkill
from .base import BaseOutputFormatter

console = Console(stderr=True)


class JsonFormatter(BaseOutputFormatter):
    """Writes skills as JSON files."""

    @property
    def format_name(self) -> str:
        return "json"

    @property
    def file_extension(self) -> str:
        return ".json"

    def _skill_to_dict(self, skill: GeneratedSkill) -> dict:
        """Convert a skill to a serializable dict."""
        return {
            "name": skill.name,
            "description": skill.description,
            "body": skill.body,
            "metadata": skill.metadata,
            "source_paper": skill.source_paper,
        }

    def format_skill(self, skill: GeneratedSkill) -> str:
        """Format a single skill as a JSON string."""
        return json.dumps(self._skill_to_dict(skill), indent=2, ensure_ascii=False)

    def format_all(self, skills: list[GeneratedSkill]) -> str:
        """Format all skills as a single JSON array."""
        data = [self._skill_to_dict(s) for s in skills]
        return json.dumps(data, indent=2, ensure_ascii=False)

    def write_skills(
        self,
        skills: list[GeneratedSkill],
        output_dir: Path,
    ) -> list[Path]:
        """Write all skills as a single JSON file.

        Creates: output_dir/skills.json
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "skills.json"

        content = self.format_all(skills)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"  Wrote: [green]{out_path}[/green] ({len(skills)} skills)")

        return [out_path]
