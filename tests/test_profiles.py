"""Tests for audience profiles."""

import pytest

from paper2skills.profiles import (
    get_profile,
    list_profiles,
    AudienceProfile,
    VALID_AUDIENCES,
    DEFAULT_AUDIENCE,
    CODING_AGENT,
    RESEARCHER,
    GENERAL,
)


class TestGetProfile:
    def test_coding_agent(self):
        p = get_profile("coding-agent")
        assert p.name == "coding-agent"
        assert p is CODING_AGENT

    def test_researcher(self):
        p = get_profile("researcher")
        assert p.name == "researcher"
        assert p is RESEARCHER

    def test_general(self):
        p = get_profile("general")
        assert p.name == "general"
        assert p is GENERAL

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown audience"):
            get_profile("nonexistent")

    def test_default_audience_is_coding_agent(self):
        assert DEFAULT_AUDIENCE == "coding-agent"


class TestListProfiles:
    def test_returns_all_profiles(self):
        profiles = list_profiles()
        assert len(profiles) == 3
        names = {p.name for p in profiles}
        assert names == {"coding-agent", "researcher", "general"}

    def test_all_profiles_are_frozen(self):
        for p in list_profiles():
            with pytest.raises(AttributeError):
                p.name = "modified"


class TestProfileContent:
    """Verify each profile has non-empty required fields."""

    @pytest.mark.parametrize("audience", VALID_AUDIENCES)
    def test_has_required_fields(self, audience):
        p = get_profile(audience)
        assert p.label
        assert p.description
        assert p.skill_definition
        assert p.extraction_focus
        assert p.output_section_headings
        assert p.rules

    @pytest.mark.parametrize("audience", VALID_AUDIENCES)
    def test_section_headings_have_when_to_use(self, audience):
        p = get_profile(audience)
        # All profiles should have some kind of "when to use" section
        assert (
            "when to use" in p.output_section_headings.lower()
            or "when" in p.output_section_headings.lower()
        )

    def test_researcher_has_method_section(self):
        p = get_profile("researcher")
        assert "## Method" in p.output_section_headings

    def test_general_has_key_insight_section(self):
        p = get_profile("general")
        assert "## Key Insight" in p.output_section_headings

    def test_researcher_has_eval_overrides(self):
        p = get_profile("researcher")
        assert p.eval_criteria_overrides  # non-empty

    def test_coding_agent_has_no_eval_overrides(self):
        p = get_profile("coding-agent")
        assert p.eval_criteria_overrides == ""
