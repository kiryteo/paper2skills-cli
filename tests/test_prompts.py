"""Tests for audience-aware prompt building and custom templates."""

import tempfile
from pathlib import Path

import pytest

from paper2skills.generate.prompts import (
    build_generation_messages,
    load_prompt_template,
    render_template,
    list_template_variables,
)
from paper2skills.evaluate.prompts import build_evaluation_system_prompt
from paper2skills.profiles import VALID_AUDIENCES


SAMPLE_METADATA = {"title": "Test Paper", "arxiv_id": "1234.56789"}
SAMPLE_TEXT = "This is a test paper about transformers."


class TestBuildGenerationMessages:
    def test_default_audience_is_coding_agent(self):
        msgs = build_generation_messages(SAMPLE_TEXT, SAMPLE_METADATA)
        assert "AI Coding Agent" in msgs[0]["content"]

    @pytest.mark.parametrize("audience", VALID_AUDIENCES)
    def test_system_prompt_mentions_audience(self, audience):
        msgs = build_generation_messages(
            SAMPLE_TEXT, SAMPLE_METADATA, audience=audience
        )
        system = msgs[0]["content"]
        # Should not contain unresolved template vars
        assert "{audience_label}" not in system
        assert "{skill_definition}" not in system
        assert "{output_section_headings}" not in system

    def test_researcher_mentions_protocol(self):
        msgs = build_generation_messages(
            SAMPLE_TEXT, SAMPLE_METADATA, audience="researcher"
        )
        system = msgs[0]["content"]
        assert "protocol" in system.lower() or "method" in system.lower()

    def test_general_mentions_insight(self):
        msgs = build_generation_messages(
            SAMPLE_TEXT, SAMPLE_METADATA, audience="general"
        )
        system = msgs[0]["content"]
        assert "insight" in system.lower()

    def test_user_prompt_has_paper_content(self):
        msgs = build_generation_messages(
            SAMPLE_TEXT, SAMPLE_METADATA, audience="researcher"
        )
        user = msgs[1]["content"]
        assert "Test Paper" in user
        assert SAMPLE_TEXT in user

    def test_invalid_audience_raises(self):
        with pytest.raises(ValueError, match="Unknown audience"):
            build_generation_messages(SAMPLE_TEXT, SAMPLE_METADATA, audience="invalid")


class TestBuildEvaluationSystemPrompt:
    def test_default_audience(self):
        prompt = build_evaluation_system_prompt()
        assert "AI Coding Agent" in prompt

    @pytest.mark.parametrize("audience", VALID_AUDIENCES)
    def test_no_unresolved_template_vars(self, audience):
        prompt = build_evaluation_system_prompt(audience)
        assert "{audience_label}" not in prompt
        assert "{audience_preposition}" not in prompt
        assert "{eval_criteria_overrides}" not in prompt

    def test_researcher_has_custom_criteria(self):
        prompt = build_evaluation_system_prompt("researcher")
        assert "RESEARCHER" in prompt

    def test_general_has_custom_criteria(self):
        prompt = build_evaluation_system_prompt("general")
        assert "GENERAL" in prompt

    def test_coding_agent_no_custom_criteria(self):
        prompt = build_evaluation_system_prompt("coding-agent")
        # Should not have the researcher/general overrides
        assert "RESEARCHER" not in prompt
        assert "GENERAL" not in prompt


# ---------------------------------------------------------------------------
# Custom prompt templates
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    def test_simple_substitution(self):
        result = render_template("Hello {{title}}", {"title": "World"})
        assert result == "Hello World"

    def test_multiple_placeholders(self):
        tpl = "{{title}} by {{authors}} ({{arxiv_id}})"
        result = render_template(
            tpl,
            {
                "title": "Attention",
                "authors": "Vaswani et al.",
                "arxiv_id": "1706.03762",
            },
        )
        assert result == "Attention by Vaswani et al. (1706.03762)"

    def test_unknown_placeholder_left_unchanged(self):
        result = render_template("{{title}} and {{unknown}}", {"title": "Hello"})
        assert result == "Hello and {{unknown}}"

    def test_no_placeholders(self):
        result = render_template("No placeholders here", {"title": "X"})
        assert result == "No placeholders here"

    def test_empty_template(self):
        result = render_template("", {"title": "X"})
        assert result == ""

    def test_repeated_placeholder(self):
        result = render_template("{{title}} and {{title}}", {"title": "Hi"})
        assert result == "Hi and Hi"


class TestLoadPromptTemplate:
    def test_load_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Custom prompt: {{title}}")
            f.flush()
            content = load_prompt_template(Path(f.name))
            assert content == "Custom prompt: {{title}}"

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_prompt_template(Path("/nonexistent/template.md"))


class TestCustomTemplateInBuildMessages:
    def test_custom_template_replaces_system_prompt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("You are a custom assistant. Paper: {{title}}")
            f.flush()
            msgs = build_generation_messages(
                SAMPLE_TEXT, SAMPLE_METADATA, prompt_template=f.name
            )
            system = msgs[0]["content"]
            assert "You are a custom assistant" in system
            assert "Paper: Test Paper" in system
            # Should NOT contain the default system prompt text
            assert "YAML-delimited markdown" not in system

    def test_custom_template_user_msg_unchanged(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Custom system prompt")
            f.flush()
            msgs = build_generation_messages(
                SAMPLE_TEXT, SAMPLE_METADATA, prompt_template=f.name
            )
            user = msgs[1]["content"]
            # User message should still contain paper content
            assert SAMPLE_TEXT in user
            assert "Test Paper" in user

    def test_custom_template_with_all_variables(self):
        metadata = {
            "title": "My Paper",
            "authors": ["Alice", "Bob"],
            "arxiv_id": "2024.12345",
            "doi": "10.1234/test",
            "abstract": "A great paper.",
        }
        tpl = (
            "Title: {{title}}\n"
            "Authors: {{authors}}\n"
            "arXiv: {{arxiv_id}}\n"
            "DOI: {{doi}}\n"
            "Abstract: {{abstract}}\n"
            "Max: {{max_skills}}\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(tpl)
            f.flush()
            msgs = build_generation_messages(
                SAMPLE_TEXT, metadata, max_skills=3, prompt_template=f.name
            )
            system = msgs[0]["content"]
            assert "Title: My Paper" in system
            assert "Authors: Alice, Bob" in system
            assert "arXiv: 2024.12345" in system
            assert "DOI: 10.1234/test" in system
            assert "Abstract: A great paper." in system
            assert "Max: 3" in system


class TestListTemplateVariables:
    def test_returns_expected_vars(self):
        variables = list_template_variables()
        assert "title" in variables
        assert "authors" in variables
        assert "content" in variables
        assert "max_skills" in variables
