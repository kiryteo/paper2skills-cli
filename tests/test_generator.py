"""Tests for skill name cleaning and LLM response parsing."""

from paper2skills.generate.generator import (
    _clean_skill_name,
    _extract_field,
    parse_skills_from_response,
    GeneratedSkill,
)


# ---------------------------------------------------------------------------
# _clean_skill_name
# ---------------------------------------------------------------------------


class TestCleanSkillName:
    def test_valid_name_unchanged(self):
        assert _clean_skill_name("multi-head-attention") == "multi-head-attention"

    def test_single_word(self):
        assert _clean_skill_name("transformer") == "transformer"

    def test_uppercase_lowered(self):
        assert _clean_skill_name("Multi-Head-Attention") == "multi-head-attention"

    def test_spaces_to_hyphens(self):
        assert _clean_skill_name("multi head attention") == "multi-head-attention"

    def test_underscores_to_hyphens(self):
        assert _clean_skill_name("multi_head_attention") == "multi-head-attention"

    def test_strips_quotes(self):
        assert _clean_skill_name('"multi-head-attention"') == "multi-head-attention"
        assert _clean_skill_name("'multi-head-attention'") == "multi-head-attention"

    def test_removes_invalid_chars(self):
        assert _clean_skill_name("multi.head!attention") == "multiheadattention"

    def test_collapses_hyphens(self):
        assert _clean_skill_name("multi--head---attention") == "multi-head-attention"

    def test_strips_leading_trailing_hyphens(self):
        assert _clean_skill_name("-multi-head-attention-") == "multi-head-attention"

    def test_truncates_to_64_chars(self):
        long_name = "a-" * 40  # 80 chars
        result = _clean_skill_name(long_name)
        assert len(result) <= 64
        # Should not end with a hyphen
        assert not result.endswith("-")

    def test_empty_string_returns_none(self):
        assert _clean_skill_name("") is None

    def test_all_invalid_chars_returns_none(self):
        assert _clean_skill_name("!!!@@@###") is None

    def test_numbers_allowed(self):
        assert _clean_skill_name("gpt-4o-mini") == "gpt-4o-mini"

    def test_leading_number(self):
        assert _clean_skill_name("4-bit-quantization") == "4-bit-quantization"


# ---------------------------------------------------------------------------
# _extract_field
# ---------------------------------------------------------------------------


class TestExtractField:
    def test_simple_field(self):
        fm = "name: my-skill\ndescription: A test skill"
        assert _extract_field(fm, "name") == "my-skill"
        assert _extract_field(fm, "description") == "A test skill"

    def test_quoted_value(self):
        fm = 'name: "my-skill"'
        assert _extract_field(fm, "name") == "my-skill"

    def test_missing_field(self):
        fm = "name: my-skill"
        assert _extract_field(fm, "description") is None


# ---------------------------------------------------------------------------
# parse_skills_from_response
# ---------------------------------------------------------------------------


class TestParseSkillsFromResponse:
    SAMPLE_RESPONSE = """---
name: scaled-dot-product-attention
description: Implement self-attention using scaled dot products
---

## When to use

Use when building transformer models.

## Instructions

1. Compute Q, K, V projections.
2. Scale by sqrt(d_k).

---SKILL_SEPARATOR---

---
name: multi-head-attention
description: Run multiple attention heads in parallel
---

## When to use

Use for capturing different types of relationships.

## Instructions

1. Split into h heads.
2. Apply attention per head.
"""

    PAPER_METADATA = {
        "title": "Attention Is All You Need",
        "arxiv_id": "1706.03762",
    }

    def test_parses_two_skills(self):
        skills = parse_skills_from_response(self.SAMPLE_RESPONSE, self.PAPER_METADATA)
        assert len(skills) == 2

    def test_skill_names(self):
        skills = parse_skills_from_response(self.SAMPLE_RESPONSE, self.PAPER_METADATA)
        names = [s.name for s in skills]
        assert "scaled-dot-product-attention" in names
        assert "multi-head-attention" in names

    def test_metadata_injected(self):
        skills = parse_skills_from_response(self.SAMPLE_RESPONSE, self.PAPER_METADATA)
        for skill in skills:
            assert skill.metadata["source-paper"] == "Attention Is All You Need"
            assert skill.metadata["arxiv-id"] == "1706.03762"

    def test_description_truncation(self):
        long_desc = "d" * 250
        response = f"---\nname: test-skill\ndescription: {long_desc}\n---\n\nBody text."
        skills = parse_skills_from_response(response, {})
        assert len(skills) == 1
        assert len(skills[0].description) <= 200
        assert skills[0].description.endswith("...")

    def test_empty_response(self):
        skills = parse_skills_from_response("", {})
        assert skills == []

    def test_no_frontmatter_skipped(self):
        skills = parse_skills_from_response("Just some text without frontmatter.", {})
        assert skills == []


# ---------------------------------------------------------------------------
# GeneratedSkill.to_skill_md
# ---------------------------------------------------------------------------


class TestGeneratedSkillToSkillMd:
    def test_roundtrip_format(self):
        skill = GeneratedSkill(
            name="test-skill",
            description="A test skill for validation",
            body="## When to use\n\nAlways.\n\n## Instructions\n\n1. Do the thing.",
            metadata={"source-paper": "Test Paper"},
        )
        md = skill.to_skill_md()
        assert md.startswith("---\n")
        assert "name: test-skill" in md
        assert "description: A test skill for validation" in md
        assert "  source-paper: Test Paper" in md
        assert "## When to use" in md

    def test_special_chars_quoted(self):
        skill = GeneratedSkill(
            name="test",
            description="Test",
            body="Body",
            metadata={"note": "value: with colon"},
        )
        md = skill.to_skill_md()
        assert '"value: with colon"' in md
