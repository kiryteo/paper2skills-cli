"""Tests for batch processing (--from-list / parse_source_list)."""

import tempfile
from pathlib import Path

import pytest

from paper2skills.cli import parse_source_list


class TestParseSourceList:
    def test_basic_sources(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("arxiv:2301.00001\n")
            f.write("10.1234/test.doi\n")
            f.write("/path/to/paper.pdf\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == [
            "arxiv:2301.00001",
            "10.1234/test.doi",
            "/path/to/paper.pdf",
        ]

    def test_blank_lines_ignored(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("arxiv:2301.00001\n")
            f.write("\n")
            f.write("   \n")
            f.write("10.1234/test.doi\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert len(sources) == 2

    def test_comment_lines_ignored(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# This is a comment\n")
            f.write("arxiv:2301.00001\n")
            f.write("# Another comment\n")
            f.write("10.1234/test.doi\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == ["arxiv:2301.00001", "10.1234/test.doi"]

    def test_inline_comments_stripped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("arxiv:2301.00001 # attention paper\n")
            f.write("10.1234/test.doi # some paper\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == ["arxiv:2301.00001", "10.1234/test.doi"]

    def test_whitespace_stripped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("  arxiv:2301.00001  \n")
            f.write("\t10.1234/test.doi\t\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == ["arxiv:2301.00001", "10.1234/test.doi"]

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == []

    def test_comments_only_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# comment 1\n")
            f.write("# comment 2\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == []

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError, match="Source list file not found"):
            parse_source_list(Path("/nonexistent/papers.txt"))

    def test_mixed_source_types(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# My papers for processing\n")
            f.write("\n")
            f.write("arxiv:2301.00001\n")
            f.write("https://arxiv.org/abs/2302.00002\n")
            f.write("10.1234/test.doi\n")
            f.write("/path/to/local.pdf\n")
            f.write("notes.txt\n")
            f.write("\n")
            f.write("# End of list\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert len(sources) == 5
        assert sources[0] == "arxiv:2301.00001"
        assert sources[1] == "https://arxiv.org/abs/2302.00002"
        assert sources[2] == "10.1234/test.doi"
        assert sources[3] == "/path/to/local.pdf"
        assert sources[4] == "notes.txt"

    def test_hash_in_url_not_treated_as_comment(self):
        """URLs with # fragments should not be truncated."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # The inline comment rule is " #" (space before #), so plain # in a URL is safe
            f.write("https://example.com/paper#section1\n")
            f.flush()
            sources = parse_source_list(Path(f.name))

        assert sources == ["https://example.com/paper#section1"]
