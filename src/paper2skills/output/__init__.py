"""Output format writers.

Supported formats:
  - opencode: OpenCode SKILL.md files (one per skill, in subdirectories)
  - json: Single JSON file with all skills
  - yaml: Single YAML file with all skills
  - markdown: Single Markdown file with all skills
"""

from __future__ import annotations

from .base import BaseOutputFormatter


# Valid format names
FORMATS = ("opencode", "json", "yaml", "markdown")


def get_formatter(format_name: str) -> BaseOutputFormatter:
    """Return a formatter instance for the given format name.

    Raises ValueError if the format is unknown.
    """
    if format_name == "opencode":
        from .opencode import OpencodeFormatter

        return OpencodeFormatter()
    elif format_name == "json":
        from .json_fmt import JsonFormatter

        return JsonFormatter()
    elif format_name == "yaml":
        from .yaml_fmt import YamlFormatter

        return YamlFormatter()
    elif format_name == "markdown":
        from .markdown_fmt import MarkdownFormatter

        return MarkdownFormatter()
    else:
        raise ValueError(
            f"Unknown output format: '{format_name}'. "
            f"Valid formats: {', '.join(FORMATS)}"
        )


def list_formats() -> list[str]:
    """Return all supported format names."""
    return list(FORMATS)
