"""Tests for audience-aware prompt building."""

import pytest

from paper2skills.generate.prompts import build_generation_messages
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
