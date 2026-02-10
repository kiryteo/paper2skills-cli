"""Audience profile definitions for skill generation.

Each profile tailors the system prompts to extract skills relevant
to a specific audience: coding agents, researchers, or a general audience.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Valid audience names
VALID_AUDIENCES = ("coding-agent", "researcher", "general")
DEFAULT_AUDIENCE = "coding-agent"


@dataclass(frozen=True)
class AudienceProfile:
    """Defines how prompts are adapted for a target audience."""

    name: str
    label: str
    description: str

    # Generation prompt fragments
    skill_definition: str
    extraction_focus: str
    output_section_headings: str
    rules: str

    # Evaluation adjustments
    eval_criteria_overrides: str


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

CODING_AGENT = AudienceProfile(
    name="coding-agent",
    label="AI Coding Agent",
    description="Extract actionable coding techniques for AI agents",
    skill_definition=(
        'A "skill" is a reusable set of instructions that teaches an AI coding '
        "agent how to apply a specific technique from a research paper when "
        "writing, reviewing, or debugging code. Skills are loaded on-demand: an "
        "agent sees the skill name and description, then decides whether to load "
        "the full content."
    ),
    extraction_focus=(
        "Extract ONLY actionable coding techniques — skip background, related work, "
        "and pure theory that has no practical coding application. Focus on techniques "
        "that an AI coding agent could practically apply when writing, reviewing, "
        "or debugging code."
    ),
    output_section_headings=(
        "## When to use\n\n"
        "Brief trigger conditions — when should an agent load this skill?\n\n"
        "## Instructions\n\n"
        "Step-by-step, actionable guidance. Use numbered steps.\n"
        "Include concrete code patterns, algorithms, or formulas where applicable.\n\n"
        "## Examples\n\n"
        "Concrete code examples demonstrating the technique.\n\n"
        "## Pitfalls\n\n"
        "Common mistakes to avoid when applying this technique."
    ),
    rules=(
        "1. Each skill must be SELF-CONTAINED — an agent reading just this skill should "
        "be able to apply the technique without reading the paper.\n"
        "2. Prefer code examples over prose. Show, don't just tell.\n"
        "3. If a technique is just common knowledge that any competent developer would "
        "know, skip it — only extract novel insights.\n"
        "4. Keep total body length under 300 lines per skill."
    ),
    eval_criteria_overrides="",  # use defaults
)

RESEARCHER = AudienceProfile(
    name="researcher",
    label="Researcher",
    description="Extract methodological techniques and experimental protocols for researchers",
    skill_definition=(
        'A "skill" is a reusable methodological recipe that teaches a researcher '
        "how to apply a specific technique, protocol, or analytical method from a "
        "paper in their own work. Skills are loaded on-demand: a researcher sees "
        "the skill name and description, then decides whether to load the full content."
    ),
    extraction_focus=(
        "Extract experimental protocols, analytical methods, statistical techniques, "
        "algorithmic approaches, and reproducible procedures. Include parameter choices, "
        "dataset requirements, and validation strategies. Skip general background and "
        "literature review content."
    ),
    output_section_headings=(
        "## When to use\n\n"
        "Conditions under which this method/protocol is applicable — what kind of "
        "problem or data does it address?\n\n"
        "## Method\n\n"
        "Step-by-step procedure. Include:\n"
        "- Required inputs and data formats\n"
        "- Parameter choices with recommended ranges/defaults\n"
        "- Equations, algorithms, or pseudocode as applicable\n\n"
        "## Validation\n\n"
        "How to verify the method is working correctly. Expected outputs, "
        "sanity checks, baseline comparisons.\n\n"
        "## Limitations\n\n"
        "Known limitations, assumptions, and failure modes."
    ),
    rules=(
        "1. Each skill must be SELF-CONTAINED — a researcher reading just this skill "
        "should be able to replicate the technique without reading the full paper.\n"
        "2. Include specific parameter values, not just vague ranges.\n"
        "3. If the technique requires specific software or libraries, name them.\n"
        "4. Distinguish between the novel contribution and standard methodology.\n"
        "5. Keep total body length under 300 lines per skill."
    ),
    eval_criteria_overrides=(
        "Adjust your evaluation for a RESEARCHER audience:\n"
        "- **Actionability**: Does it contain enough detail to reproduce the method? "
        "Are parameters, inputs, and expected outputs specified?\n"
        "- **Specificity**: Does the description clearly define what kind of research "
        "problem this addresses?\n"
        "- **Novelty**: Does it go beyond textbook methods? Score higher if it contains "
        "specific parameter choices or tricks from the paper.\n"
        "- **Correctness**: Are the statistical methods, equations, and procedures sound?"
    ),
)

GENERAL = AudienceProfile(
    name="general",
    label="General",
    description="Extract key insights and practical takeaways for a broad audience",
    skill_definition=(
        'A "skill" is a concise, practical takeaway that teaches someone the core '
        "insight or technique from a research paper in an accessible way. Skills are "
        "loaded on-demand: a reader sees the skill name and description, then decides "
        "whether to load the full content."
    ),
    extraction_focus=(
        "Extract the key insights, practical applications, and core techniques from "
        "the paper. Translate technical jargon into clear language. Focus on ideas that "
        "someone could apply in practice, even without deep domain expertise."
    ),
    output_section_headings=(
        "## When to use\n\n"
        "In what situations is this insight or technique relevant?\n\n"
        "## Key Insight\n\n"
        "The core idea explained clearly and concisely. Use analogies where helpful.\n\n"
        "## How to Apply\n\n"
        "Practical steps to use this insight. Include concrete examples.\n\n"
        "## Watch Out For\n\n"
        "Common misconceptions or mistakes when applying this idea."
    ),
    rules=(
        "1. Each skill must be SELF-CONTAINED — a reader should understand the technique "
        "without reading the paper.\n"
        "2. Avoid unnecessary jargon. If a technical term is essential, define it.\n"
        "3. Use concrete examples and analogies to clarify abstract concepts.\n"
        "4. Focus on practical applicability over theoretical completeness.\n"
        "5. Keep total body length under 300 lines per skill."
    ),
    eval_criteria_overrides=(
        "Adjust your evaluation for a GENERAL audience:\n"
        "- **Actionability**: Can someone without deep domain expertise follow the "
        "instructions? Are examples concrete and relatable?\n"
        "- **Specificity**: Is the description clear about when to use this skill?\n"
        "- **Conciseness**: Is jargon minimized? Is the signal-to-noise ratio high?\n"
        "- **Novelty**: Does it provide a genuinely useful insight, not just a summary?"
    ),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROFILES: dict[str, AudienceProfile] = {
    "coding-agent": CODING_AGENT,
    "researcher": RESEARCHER,
    "general": GENERAL,
}


def get_profile(name: str) -> AudienceProfile:
    """Look up a profile by name. Raises ValueError if not found."""
    profile = _PROFILES.get(name)
    if profile is None:
        valid = ", ".join(sorted(_PROFILES))
        raise ValueError(f"Unknown audience '{name}'. Valid audiences: {valid}")
    return profile


def list_profiles() -> list[AudienceProfile]:
    """Return all registered profiles."""
    return list(_PROFILES.values())
