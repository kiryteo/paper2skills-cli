"""Skill quality evaluation and scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.table import Table

from ..generate.generator import GeneratedSkill
from ..providers.base import BaseLLMProvider
from .prompts import (
    EVALUATION_USER_PROMPT,
    build_evaluation_system_prompt,
)

console = Console(stderr=True)


@dataclass
class SkillScore:
    """Evaluation scores for a single skill."""

    name: str
    actionability: float = 0
    specificity: float = 0
    conciseness: float = 0
    novelty: float = 0
    correctness: float = 0
    average_score: float = 0
    verdict: str = "discard"
    summary: str = ""
    improvements: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Full evaluation report for a set of skills."""

    scores: list[SkillScore] = field(default_factory=list)
    total_skills: int = 0
    keep_count: int = 0
    improve_count: int = 0
    discard_count: int = 0

    def to_markdown(self) -> str:
        """Render the report as markdown."""
        lines = ["# Skill Evaluation Report", ""]
        lines.append(f"Total skills evaluated: **{self.total_skills}**")
        lines.append(f"- Keep: **{self.keep_count}**")
        lines.append(f"- Improve: **{self.improve_count}**")
        lines.append(f"- Discard: **{self.discard_count}**")
        lines.append("")

        # Sort by average score descending
        sorted_scores = sorted(self.scores, key=lambda s: s.average_score, reverse=True)

        lines.append("## Rankings")
        lines.append("")
        lines.append("| Rank | Skill | Avg | Act | Spc | Con | Nov | Cor | Verdict |")
        lines.append("|------|-------|-----|-----|-----|-----|-----|-----|---------|")

        for i, score in enumerate(sorted_scores, 1):
            verdict_icon = {
                "keep": "KEEP",
                "improve": "IMPROVE",
                "discard": "DISCARD",
            }.get(score.verdict, "?")
            lines.append(
                f"| {i} | {score.name} | {score.average_score:.1f} | "
                f"{score.actionability:.0f} | {score.specificity:.0f} | "
                f"{score.conciseness:.0f} | {score.novelty:.0f} | "
                f"{score.correctness:.0f} | {verdict_icon} |"
            )

        lines.append("")
        lines.append("## Detailed Assessments")
        lines.append("")

        for score in sorted_scores:
            lines.append(f"### {score.name} ({score.verdict.upper()})")
            lines.append(f"**Score: {score.average_score:.1f}/10**")
            lines.append("")
            lines.append(score.summary)
            lines.append("")
            if score.improvements:
                lines.append("**Suggested improvements:**")
                for imp in score.improvements:
                    lines.append(f"- {imp}")
                lines.append("")

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print a summary table to the console."""
        table = Table(title="Skill Evaluation Results")
        table.add_column("Skill", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Verdict", justify="center")
        table.add_column("Summary", max_width=50)

        sorted_scores = sorted(self.scores, key=lambda s: s.average_score, reverse=True)

        for score in sorted_scores:
            verdict_style = {
                "keep": "green",
                "improve": "yellow",
                "discard": "red",
            }.get(score.verdict, "white")

            table.add_row(
                score.name,
                f"{score.average_score:.1f}",
                f"[{verdict_style}]{score.verdict.upper()}[/{verdict_style}]",
                score.summary[:50] + "..."
                if len(score.summary) > 50
                else score.summary,
            )

        console.print(table)


def evaluate_skill(
    skill: GeneratedSkill,
    provider: BaseLLMProvider,
    audience: Optional[str] = None,
) -> SkillScore:
    """Evaluate a single skill using the LLM."""
    user_msg = EVALUATION_USER_PROMPT.format(
        name=skill.name,
        description=skill.description,
        body=skill.body,
    )

    messages = [
        {"role": "system", "content": build_evaluation_system_prompt(audience)},
        {"role": "user", "content": user_msg},
    ]

    response = provider.chat(messages, temperature=0.1, max_tokens=1024)

    # Parse JSON response
    try:
        # Strip any markdown code fences if present
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        data = json.loads(content)
    except json.JSONDecodeError:
        console.print(
            f"[yellow]  Warning: could not parse evaluation for '{skill.name}', "
            f"using default scores[/yellow]"
        )
        return SkillScore(name=skill.name, summary="Evaluation parsing failed")

    scores = data.get("scores", {})
    return SkillScore(
        name=skill.name,
        actionability=scores.get("actionability", 0),
        specificity=scores.get("specificity", 0),
        conciseness=scores.get("conciseness", 0),
        novelty=scores.get("novelty", 0),
        correctness=scores.get("correctness", 0),
        average_score=data.get("average_score", 0),
        verdict=data.get("verdict", "discard"),
        summary=data.get("summary", ""),
        improvements=data.get("improvements", []),
    )


def evaluate_skills(
    skills: list[GeneratedSkill],
    provider: BaseLLMProvider,
    audience: Optional[str] = None,
) -> EvaluationReport:
    """Evaluate a list of skills and produce a report."""
    report = EvaluationReport(total_skills=len(skills))

    for i, skill in enumerate(skills, 1):
        console.print(
            f"  Evaluating skill {i}/{len(skills)}: [cyan]{skill.name}[/cyan]"
        )
        score = evaluate_skill(skill, provider, audience)
        report.scores.append(score)

        if score.verdict == "keep":
            report.keep_count += 1
        elif score.verdict == "improve":
            report.improve_count += 1
        else:
            report.discard_count += 1

    return report
