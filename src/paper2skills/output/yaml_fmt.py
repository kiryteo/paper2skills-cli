"""YAML output formatter."""

from __future__ import annotations

from pathlib import Path

import yaml
from rich.console import Console

from ..generate.generator import GeneratedSkill
from .base import BaseOutputFormatter

console = Console(stderr=True)


class YamlFormatter(BaseOutputFormatter):
    """Writes skills as YAML files."""

    @property
    def format_name(self) -> str:
        return "yaml"

    @property
    def file_extension(self) -> str:
        return ".yaml"

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
        """Format a single skill as a YAML string."""
        return yaml.dump(
            self._skill_to_dict(skill),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def format_all(self, skills: list[GeneratedSkill]) -> str:
        """Format all skills as a YAML list."""
        data = [self._skill_to_dict(s) for s in skills]
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def write_skills(
        self,
        skills: list[GeneratedSkill],
        output_dir: Path,
    ) -> list[Path]:
        """Write all skills as a single YAML file.

        Creates: output_dir/skills.yaml
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "skills.yaml"

        content = self.format_all(skills)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"  Wrote: [green]{out_path}[/green] ({len(skills)} skills)")

        return [out_path]
