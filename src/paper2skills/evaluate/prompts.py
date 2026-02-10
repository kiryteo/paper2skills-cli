"""Prompt templates for skill evaluation."""

from __future__ import annotations

from typing import Optional

from ..profiles import AudienceProfile, get_profile, DEFAULT_AUDIENCE

EVALUATION_SYSTEM_PROMPT = """\
You are an expert at evaluating the quality and usefulness of skill files \
targeted at {audience_label}. \
You assess whether a skill definition is actionable, specific, concise, novel, and \
technically correct.

You will be given a SKILL.md file and must score it on 5 criteria, each from 1-10.

## Output Format

You MUST output valid JSON with exactly this structure:

{{
  "scores": {{
    "actionability": <1-10>,
    "specificity": <1-10>,
    "conciseness": <1-10>,
    "novelty": <1-10>,
    "correctness": <1-10>
  }},
  "average_score": <float>,
  "verdict": "keep" | "improve" | "discard",
  "summary": "<2-3 sentence assessment>",
  "improvements": ["<specific suggestion 1>", "<specific suggestion 2>"]
}}

## Scoring Criteria

1. **Actionability** (1-10): Does the skill contain concrete, step-by-step instructions \
that {audience_preposition} can follow? Code examples? Algorithms? Score 1 if it's pure \
theory, 10 if every section has executable guidance.

2. **Specificity** (1-10): Is the description precise enough to know \
WHEN to load this skill? Does it clearly define its scope? Score 1 if vague/generic, \
10 if one can confidently decide to load or skip it.

3. **Conciseness** (1-10): What's the signal-to-noise ratio? Score 1 if full of \
filler and repetition, 10 if every line adds value.

4. **Novelty** (1-10): Does it teach something beyond common knowledge? \
Score 1 if it's just repackaging obvious best practices, \
10 if it contains genuinely new techniques or insights.

5. **Correctness** (1-10): Are the technical claims, examples, and \
procedures correct? Score 1 if full of errors, 10 if technically sound.

{eval_criteria_overrides}

## Verdict Rules

- "keep": average_score >= 7.0
- "improve": average_score >= 4.0 and < 7.0
- "discard": average_score < 4.0

Output ONLY the JSON. No preamble, no commentary, no markdown code fences.
"""

# Audience prepositions for natural phrasing in eval prompts
_EVAL_PREPOSITIONS = {
    "coding-agent": "an AI coding agent",
    "researcher": "a researcher",
    "general": "a reader",
}

EVALUATION_USER_PROMPT = """\
Evaluate the following SKILL.md file:

---
Name: {name}
Description: {description}
---

{body}
"""


def build_evaluation_system_prompt(audience: Optional[str] = None) -> str:
    """Build the evaluation system prompt for a given audience."""
    profile = get_profile(audience or DEFAULT_AUDIENCE)
    preposition = _EVAL_PREPOSITIONS.get(profile.name, "a reader")
    return EVALUATION_SYSTEM_PROMPT.format(
        audience_label=profile.label,
        audience_preposition=preposition,
        eval_criteria_overrides=profile.eval_criteria_overrides,
    )


OVERLAP_SYSTEM_PROMPT = """\
You are an expert at detecting overlap and redundancy between AI agent skill files. \
Given pairs of skills, you determine if they should be merged into a single skill.

## Output Format

You MUST output valid JSON with exactly this structure:

{
  "pairs": [
    {
      "skill_a": "<name>",
      "skill_b": "<name>",
      "overlap_score": <0.0-1.0>,
      "should_merge": true | false,
      "reason": "<why they should/shouldn't merge>",
      "suggested_merged_name": "<name if merging>" | null
    }
  ]
}

## Rules

- overlap_score 0.0 = completely unrelated, 1.0 = nearly identical
- should_merge = true when overlap_score >= 0.7 AND merging would produce a \
better single skill than two separate ones
- When skills cover the same technique from different angles, they should merge
- When skills cover genuinely distinct techniques that happen to be from the same \
domain, they should NOT merge

Output ONLY the JSON. No preamble, no commentary, no markdown code fences.
"""

OVERLAP_USER_PROMPT = """\
Analyze the following pairs of skills for overlap and potential merging:

{skills_text}
"""

MERGE_SYSTEM_PROMPT = """\
You are an expert at consolidating overlapping AI agent skill files into a single, \
improved skill. You combine the best parts of each source skill while eliminating \
redundancy.

## Output Format

Output the merged skill in SKILL.md format:

```
---
name: merged-skill-name
description: Clear one-line description (under 200 chars)
metadata:
  source-papers: "Paper A; Paper B"
  merged-from: "skill-a, skill-b"
---

## When to use

Combined trigger conditions.

## Instructions

Consolidated step-by-step guidance.

## Examples

Best examples from both skills, deduplicated.

## Pitfalls

Combined pitfalls from both skills.
```

## Rules

1. The merged skill should be BETTER than either source skill alone
2. Eliminate redundancy — don't repeat the same information twice
3. Keep the most specific and actionable content from each source
4. The name should be descriptive of the combined technique
5. Body should be under 300 lines

Output ONLY the merged SKILL.md content. No preamble, no commentary.
"""

MERGE_USER_PROMPT = """\
Merge the following overlapping skills into a single, consolidated skill:

## Skill A: {name_a}
{content_a}

## Skill B: {name_b}
{content_b}
"""
