"""Base output formatter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..generate.generator import GeneratedSkill


class BaseOutputFormatter(ABC):
    """Abstract base for output format writers."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Short identifier for this format (e.g. 'json', 'yaml')."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension including dot (e.g. '.json')."""

    @abstractmethod
    def write_skills(
        self,
        skills: list[GeneratedSkill],
        output_dir: Path,
    ) -> list[Path]:
        """Write skills to the output directory.

        Returns list of paths to written files.
        """

    @abstractmethod
    def format_skill(self, skill: GeneratedSkill) -> str:
        """Format a single skill as a string in this format."""

    @abstractmethod
    def format_all(self, skills: list[GeneratedSkill]) -> str:
        """Format all skills as a single string."""
