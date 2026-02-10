"""Tests for output format plugins."""

import json
import tempfile
from pathlib import Path

import yaml

from paper2skills.generate.generator import GeneratedSkill
from paper2skills.output import get_formatter, list_formats, FORMATS
from paper2skills.output.base import BaseOutputFormatter
from paper2skills.output.opencode import OpencodeFormatter
from paper2skills.output.json_fmt import JsonFormatter
from paper2skills.output.yaml_fmt import YamlFormatter
from paper2skills.output.markdown_fmt import MarkdownFormatter

import pytest


def _make_skill(name="test-skill", description="A test skill", body=None):
    return GeneratedSkill(
        name=name,
        description=description,
        body=body or "## When to use\n\nAlways.\n\n## Instructions\n\n1. Do it.",
        metadata={
            "source-paper": "Test Paper",
            "arxiv-id": "1234.56789",
        },
        source_paper="Test Paper",
    )


def _make_skills():
    return [
        _make_skill("alpha-skill", "First skill"),
        _make_skill("beta-skill", "Second skill"),
        _make_skill("gamma-skill", "Third skill"),
    ]


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestFormatRegistry:
    def test_list_formats(self):
        fmts = list_formats()
        assert "opencode" in fmts
        assert "json" in fmts
        assert "yaml" in fmts
        assert "markdown" in fmts

    def test_formats_tuple(self):
        assert FORMATS == ("opencode", "json", "yaml", "markdown")

    def test_get_opencode_formatter(self):
        fmt = get_formatter("opencode")
        assert isinstance(fmt, OpencodeFormatter)
        assert isinstance(fmt, BaseOutputFormatter)

    def test_get_json_formatter(self):
        fmt = get_formatter("json")
        assert isinstance(fmt, JsonFormatter)
        assert isinstance(fmt, BaseOutputFormatter)

    def test_get_yaml_formatter(self):
        fmt = get_formatter("yaml")
        assert isinstance(fmt, YamlFormatter)
        assert isinstance(fmt, BaseOutputFormatter)

    def test_get_markdown_formatter(self):
        fmt = get_formatter("markdown")
        assert isinstance(fmt, MarkdownFormatter)
        assert isinstance(fmt, BaseOutputFormatter)

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown output format"):
            get_formatter("pdf")

    def test_format_names_match(self):
        for name in FORMATS:
            fmt = get_formatter(name)
            assert fmt.format_name == name


# ---------------------------------------------------------------------------
# OpencodeFormatter tests
# ---------------------------------------------------------------------------


class TestOpencodeFormatter:
    def test_format_name(self):
        fmt = OpencodeFormatter()
        assert fmt.format_name == "opencode"
        assert fmt.file_extension == ".md"

    def test_format_skill(self):
        fmt = OpencodeFormatter()
        skill = _make_skill()
        result = fmt.format_skill(skill)
        assert "---" in result
        assert "name: test-skill" in result
        assert "description: A test skill" in result

    def test_format_all(self):
        fmt = OpencodeFormatter()
        skills = _make_skills()
        result = fmt.format_all(skills)
        assert "alpha-skill" in result
        assert "beta-skill" in result
        assert "gamma-skill" in result

    def test_write_skills(self):
        fmt = OpencodeFormatter()
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = _make_skills()
            paths = fmt.write_skills(skills, Path(tmpdir))

            assert len(paths) == 3
            for p in paths:
                assert p.exists()
                assert p.name == "SKILL.md"

            # Check directory structure
            dirs = {p.parent.name for p in paths}
            assert dirs == {"alpha-skill", "beta-skill", "gamma-skill"}


# ---------------------------------------------------------------------------
# JsonFormatter tests
# ---------------------------------------------------------------------------


class TestJsonFormatter:
    def test_format_name(self):
        fmt = JsonFormatter()
        assert fmt.format_name == "json"
        assert fmt.file_extension == ".json"

    def test_format_skill(self):
        fmt = JsonFormatter()
        skill = _make_skill()
        result = fmt.format_skill(skill)
        data = json.loads(result)
        assert data["name"] == "test-skill"
        assert data["description"] == "A test skill"
        assert data["metadata"]["source-paper"] == "Test Paper"
        assert data["source_paper"] == "Test Paper"

    def test_format_all(self):
        fmt = JsonFormatter()
        skills = _make_skills()
        result = fmt.format_all(skills)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3
        names = {s["name"] for s in data}
        assert names == {"alpha-skill", "beta-skill", "gamma-skill"}

    def test_write_skills(self):
        fmt = JsonFormatter()
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = _make_skills()
            paths = fmt.write_skills(skills, Path(tmpdir))

            assert len(paths) == 1
            assert paths[0].name == "skills.json"
            assert paths[0].exists()

            data = json.loads(paths[0].read_text())
            assert len(data) == 3

    def test_format_skill_preserves_body(self):
        fmt = JsonFormatter()
        skill = _make_skill(body="Line 1\nLine 2\n\n## Section\nContent")
        result = fmt.format_skill(skill)
        data = json.loads(result)
        assert "Line 1\nLine 2" in data["body"]
        assert "## Section" in data["body"]

    def test_empty_skills_list(self):
        fmt = JsonFormatter()
        result = fmt.format_all([])
        data = json.loads(result)
        assert data == []


# ---------------------------------------------------------------------------
# YamlFormatter tests
# ---------------------------------------------------------------------------


class TestYamlFormatter:
    def test_format_name(self):
        fmt = YamlFormatter()
        assert fmt.format_name == "yaml"
        assert fmt.file_extension == ".yaml"

    def test_format_skill(self):
        fmt = YamlFormatter()
        skill = _make_skill()
        result = fmt.format_skill(skill)
        data = yaml.safe_load(result)
        assert data["name"] == "test-skill"
        assert data["description"] == "A test skill"
        assert data["metadata"]["source-paper"] == "Test Paper"

    def test_format_all(self):
        fmt = YamlFormatter()
        skills = _make_skills()
        result = fmt.format_all(skills)
        data = yaml.safe_load(result)
        assert isinstance(data, list)
        assert len(data) == 3
        names = {s["name"] for s in data}
        assert names == {"alpha-skill", "beta-skill", "gamma-skill"}

    def test_write_skills(self):
        fmt = YamlFormatter()
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = _make_skills()
            paths = fmt.write_skills(skills, Path(tmpdir))

            assert len(paths) == 1
            assert paths[0].name == "skills.yaml"
            assert paths[0].exists()

            data = yaml.safe_load(paths[0].read_text())
            assert len(data) == 3

    def test_empty_skills_list(self):
        fmt = YamlFormatter()
        result = fmt.format_all([])
        data = yaml.safe_load(result)
        assert data == []


# ---------------------------------------------------------------------------
# MarkdownFormatter tests
# ---------------------------------------------------------------------------


class TestMarkdownFormatter:
    def test_format_name(self):
        fmt = MarkdownFormatter()
        assert fmt.format_name == "markdown"
        assert fmt.file_extension == ".md"

    def test_format_skill(self):
        fmt = MarkdownFormatter()
        skill = _make_skill()
        result = fmt.format_skill(skill)
        assert "## test-skill" in result
        assert "**A test skill**" in result
        assert "| source-paper | Test Paper |" in result

    def test_format_all(self):
        fmt = MarkdownFormatter()
        skills = _make_skills()
        result = fmt.format_all(skills)
        assert "# Generated Skills" in result
        assert "Total: 3 skills" in result
        assert "## alpha-skill" in result
        assert "## beta-skill" in result
        assert "## gamma-skill" in result
        # Separators between skills
        assert "---" in result

    def test_write_skills(self):
        fmt = MarkdownFormatter()
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = _make_skills()
            paths = fmt.write_skills(skills, Path(tmpdir))

            assert len(paths) == 1
            assert paths[0].name == "skills.md"
            assert paths[0].exists()

            content = paths[0].read_text()
            assert "# Generated Skills" in content

    def test_format_skill_no_metadata(self):
        fmt = MarkdownFormatter()
        skill = GeneratedSkill(
            name="bare-skill",
            description="No metadata",
            body="Just a body.",
            metadata={},
        )
        result = fmt.format_skill(skill)
        assert "## bare-skill" in result
        assert "**No metadata**" in result
        # No table should appear
        assert "| Key |" not in result

    def test_format_all_single_skill(self):
        fmt = MarkdownFormatter()
        skill = _make_skill()
        result = fmt.format_all([skill])
        assert "# Generated Skills" in result
        assert "Total: 1 skills" in result
        # No separator for single skill
        lines = result.split("\n")
        separator_count = sum(1 for line in lines if line.strip() == "---")
        assert separator_count == 0


# ---------------------------------------------------------------------------
# Cross-format consistency tests
# ---------------------------------------------------------------------------


class TestCrossFormatConsistency:
    def test_all_formatters_write_to_output_dir(self):
        """Every formatter should create the output directory if needed."""
        skills = _make_skills()
        for name in FORMATS:
            fmt = get_formatter(name)
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "nested" / "output"
                paths = fmt.write_skills(skills, out)
                assert out.exists()
                for p in paths:
                    assert p.exists()

    def test_all_formatters_handle_empty_list(self):
        """Every formatter should handle an empty skills list."""
        for name in FORMATS:
            fmt = get_formatter(name)
            result = fmt.format_all([])
            assert isinstance(result, str)

    def test_all_formatters_have_format_skill(self):
        """Every formatter should produce non-empty output for a single skill."""
        skill = _make_skill()
        for name in FORMATS:
            fmt = get_formatter(name)
            result = fmt.format_skill(skill)
            assert len(result) > 0
            assert "test-skill" in result
