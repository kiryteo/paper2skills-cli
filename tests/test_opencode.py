"""Tests for SKILL.md write/read round-trip."""

import tempfile
from pathlib import Path

from paper2skills.generate.generator import GeneratedSkill
from paper2skills.output.opencode import write_skills, read_existing_skills


class TestSkillRoundTrip:
    def _make_skill(self, name="test-skill", description="A test skill", body=None):
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

    def test_write_creates_directory_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = self._make_skill()
            paths = write_skills([skill], Path(tmpdir))

            assert len(paths) == 1
            assert paths[0].exists()
            assert paths[0].name == "SKILL.md"
            assert paths[0].parent.name == "test-skill"

    def test_write_read_roundtrip_single(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._make_skill()
            write_skills([original], Path(tmpdir))
            loaded = read_existing_skills(Path(tmpdir))

            assert len(loaded) == 1
            assert loaded[0].name == original.name
            assert loaded[0].description == original.description
            assert "## When to use" in loaded[0].body
            assert loaded[0].metadata["source-paper"] == "Test Paper"
            assert loaded[0].metadata["arxiv-id"] == "1234.56789"

    def test_write_read_roundtrip_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = [
                self._make_skill("alpha-skill", "First skill"),
                self._make_skill("beta-skill", "Second skill"),
                self._make_skill("gamma-skill", "Third skill"),
            ]
            write_skills(skills, Path(tmpdir))
            loaded = read_existing_skills(Path(tmpdir))

            assert len(loaded) == 3
            loaded_names = {s.name for s in loaded}
            assert loaded_names == {"alpha-skill", "beta-skill", "gamma-skill"}

    def test_read_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = read_existing_skills(Path(tmpdir))
            assert loaded == []

    def test_read_nonexistent_directory(self):
        loaded = read_existing_skills(Path("/nonexistent/path"))
        assert loaded == []

    def test_read_skips_non_skill_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a valid skill
            skill = self._make_skill()
            write_skills([skill], Path(tmpdir))

            # Create a directory without SKILL.md
            (Path(tmpdir) / "not-a-skill").mkdir()

            # Create a regular file (not a directory)
            (Path(tmpdir) / "random-file.txt").write_text("hello")

            loaded = read_existing_skills(Path(tmpdir))
            assert len(loaded) == 1
            assert loaded[0].name == "test-skill"

    def test_overwrite_existing_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = self._make_skill(description="Version 1")
            write_skills([v1], Path(tmpdir))

            v2 = self._make_skill(description="Version 2")
            write_skills([v2], Path(tmpdir))

            loaded = read_existing_skills(Path(tmpdir))
            assert len(loaded) == 1
            assert loaded[0].description == "Version 2"
