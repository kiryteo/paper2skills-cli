"""Skill overlap detection and merging."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from rich.console import Console

from ..generate.generator import GeneratedSkill, parse_skills_from_response
from ..providers.base import BaseLLMProvider
from .prompts import (
    OVERLAP_SYSTEM_PROMPT,
    OVERLAP_USER_PROMPT,
    MERGE_SYSTEM_PROMPT,
    MERGE_USER_PROMPT,
)

console = Console(stderr=True)


@dataclass
class OverlapPair:
    """Detected overlap between two skills."""

    skill_a: str
    skill_b: str
    overlap_score: float
    should_merge: bool
    reason: str
    suggested_name: Optional[str] = None


@dataclass
class MergeReport:
    """Report on overlap analysis and merge suggestions."""

    pairs: list[OverlapPair] = field(default_factory=list)
    merge_groups: list[list[str]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render as markdown."""
        lines = ["# Merge Analysis Report", ""]

        if not self.pairs:
            lines.append("No overlapping skill pairs detected.")
            return "\n".join(lines)

        # Show all pairs
        lines.append("## Overlap Pairs")
        lines.append("")
        lines.append("| Skill A | Skill B | Overlap | Merge? | Reason |")
        lines.append("|---------|---------|---------|--------|--------|")

        for pair in sorted(self.pairs, key=lambda p: p.overlap_score, reverse=True):
            merge = "YES" if pair.should_merge else "no"
            lines.append(
                f"| {pair.skill_a} | {pair.skill_b} | "
                f"{pair.overlap_score:.0%} | {merge} | {pair.reason} |"
            )

        lines.append("")

        # Show merge groups
        if self.merge_groups:
            lines.append("## Suggested Merge Groups")
            lines.append("")
            for i, group in enumerate(self.merge_groups, 1):
                lines.append(f"{i}. Merge: **{', '.join(group)}**")
            lines.append("")

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print a quick summary to console."""
        merge_pairs = [p for p in self.pairs if p.should_merge]
        console.print(
            f"  Found [yellow]{len(merge_pairs)}[/yellow] pairs recommended for merging "
            f"out of {len(self.pairs)} total pairs analyzed"
        )
        for pair in merge_pairs:
            console.print(
                f"    [yellow]{pair.skill_a}[/yellow] + "
                f"[yellow]{pair.skill_b}[/yellow] "
                f"(overlap: {pair.overlap_score:.0%})"
            )


def detect_overlaps(
    skills: list[GeneratedSkill],
    provider: BaseLLMProvider,
    threshold: float = 0.7,
) -> MergeReport:
    """Detect overlapping skills using LLM analysis.

    For small sets (<= 10 skills), analyzes all pairs.
    For larger sets, uses embeddings for initial filtering.
    """
    if len(skills) < 2:
        return MergeReport()

    report = MergeReport()

    if len(skills) <= 10:
        # Analyze all pairs via LLM
        report = _analyze_pairs_llm(skills, provider)
    else:
        # Use embeddings for pre-filtering, then LLM for detailed analysis
        try:
            report = _analyze_pairs_embeddings(skills, provider, threshold)
        except NotImplementedError:
            console.print(
                "  [yellow]Embeddings not supported by this provider. "
                "Using LLM-only overlap analysis (slower for large sets).[/yellow]"
            )
            report = _analyze_pairs_llm(skills, provider)

    # Build merge groups from pairs
    report.merge_groups = _build_merge_groups(report.pairs)

    return report


def _analyze_pairs_llm(
    skills: list[GeneratedSkill],
    provider: BaseLLMProvider,
) -> MergeReport:
    """Analyze all skill pairs using LLM for overlap detection."""
    # Build a text block with all skills
    skills_text_parts = []
    for i, skill in enumerate(skills):
        skills_text_parts.append(
            f"### Skill {i + 1}: {skill.name}\n"
            f"Description: {skill.description}\n\n"
            f"{skill.body[:500]}{'...' if len(skill.body) > 500 else ''}\n"
        )

    # Ask about all pairs at once
    pair_descriptions = []
    for a, b in combinations(range(len(skills)), 2):
        pair_descriptions.append(f'- Pair: "{skills[a].name}" vs "{skills[b].name}"')

    skills_text = "\n---\n".join(skills_text_parts)
    skills_text += "\n\n## Pairs to analyze:\n" + "\n".join(pair_descriptions)

    messages = [
        {"role": "system", "content": OVERLAP_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": OVERLAP_USER_PROMPT.format(skills_text=skills_text),
        },
    ]

    console.print("  Analyzing skill pairs for overlap...")
    response = provider.chat(messages, temperature=0.1, max_tokens=2048)

    report = MergeReport()

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        data = json.loads(content)
    except json.JSONDecodeError:
        console.print("[yellow]  Warning: could not parse overlap analysis[/yellow]")
        return report

    for pair_data in data.get("pairs", []):
        report.pairs.append(
            OverlapPair(
                skill_a=pair_data.get("skill_a", ""),
                skill_b=pair_data.get("skill_b", ""),
                overlap_score=pair_data.get("overlap_score", 0),
                should_merge=pair_data.get("should_merge", False),
                reason=pair_data.get("reason", ""),
                suggested_name=pair_data.get("suggested_merged_name"),
            )
        )

    return report


def _analyze_pairs_embeddings(
    skills: list[GeneratedSkill],
    provider: BaseLLMProvider,
    threshold: float,
) -> MergeReport:
    """Use embeddings for initial overlap filtering, then LLM for detailed analysis."""
    import math

    console.print("  Computing skill embeddings for pre-filtering...")

    # Create text representations for embedding
    texts = [f"{s.name}: {s.description}\n{s.body[:300]}" for s in skills]

    embeddings = provider.get_embeddings(texts)

    # Find pairs with high cosine similarity
    candidate_pairs: list[tuple[int, int, float]] = []
    for i, j in combinations(range(len(skills)), 2):
        sim = _cosine_similarity(embeddings[i], embeddings[j])
        if sim >= threshold * 0.7:  # Lower threshold for pre-filtering
            candidate_pairs.append((i, j, sim))

    console.print(
        f"  Found {len(candidate_pairs)} candidate pairs from embedding similarity"
    )

    if not candidate_pairs:
        return MergeReport()

    # Analyze candidates with LLM
    candidate_skills = set()
    for i, j, _ in candidate_pairs:
        candidate_skills.add(i)
        candidate_skills.add(j)

    filtered_skills = [skills[i] for i in sorted(candidate_skills)]
    return _analyze_pairs_llm(filtered_skills, provider)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_merge_groups(pairs: list[OverlapPair]) -> list[list[str]]:
    """Build connected groups from merge-recommended pairs (union-find)."""
    merge_pairs = [p for p in pairs if p.should_merge]
    if not merge_pairs:
        return []

    # Simple union-find
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for pair in merge_pairs:
        union(pair.skill_a, pair.skill_b)

    # Collect groups
    groups: dict[str, list[str]] = {}
    for name in parent:
        root = find(name)
        groups.setdefault(root, []).append(name)

    return [sorted(group) for group in groups.values() if len(group) > 1]


def merge_skills(
    skill_a: GeneratedSkill,
    skill_b: GeneratedSkill,
    provider: BaseLLMProvider,
) -> Optional[GeneratedSkill]:
    """Merge two overlapping skills into one consolidated skill."""
    user_msg = MERGE_USER_PROMPT.format(
        name_a=skill_a.name,
        content_a=skill_a.to_skill_md(),
        name_b=skill_b.name,
        content_b=skill_b.to_skill_md(),
    )

    messages = [
        {"role": "system", "content": MERGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    console.print(
        f"  Merging [cyan]{skill_a.name}[/cyan] + [cyan]{skill_b.name}[/cyan]..."
    )
    response = provider.chat(messages, temperature=0.2, max_tokens=4096)

    # Parse the merged skill
    combined_metadata = {
        **skill_a.metadata,
        **skill_b.metadata,
        "merged-from": f"{skill_a.name}, {skill_b.name}",
    }

    # Combine source papers
    papers = set()
    for s in [skill_a, skill_b]:
        if s.source_paper:
            papers.add(s.source_paper)
    if papers:
        combined_metadata["source-papers"] = "; ".join(sorted(papers))

    skills = parse_skills_from_response(response.content, {"title": "merged"})
    if skills:
        merged = skills[0]
        merged.metadata.update(combined_metadata)
        return merged

    console.print("[yellow]  Warning: merge produced no valid skill[/yellow]")
    return None


def merge_into_existing(
    new_skills: list[GeneratedSkill],
    existing_skills: list[GeneratedSkill],
    provider: BaseLLMProvider,
    threshold: float = 0.7,
) -> tuple[list[GeneratedSkill], list[GeneratedSkill]]:
    """Merge new skills into existing ones where overlap is found.

    Returns:
        (merged_skills, novel_skills) — merged replacements and truly new skills
    """
    if not existing_skills:
        return [], new_skills

    all_skills = existing_skills + new_skills
    report = detect_overlaps(all_skills, provider, threshold)

    # Find new skills that overlap with existing ones
    existing_names = {s.name for s in existing_skills}
    new_names = {s.name for s in new_skills}

    merged_results: list[GeneratedSkill] = []
    merged_new_names: set[str] = set()

    for pair in report.pairs:
        if not pair.should_merge:
            continue

        # We only care about cross-set merges (new into existing)
        a_is_existing = pair.skill_a in existing_names
        b_is_existing = pair.skill_b in existing_names
        a_is_new = pair.skill_a in new_names
        b_is_new = pair.skill_b in new_names

        if (a_is_existing and b_is_new) or (a_is_new and b_is_existing):
            existing_name = pair.skill_a if a_is_existing else pair.skill_b
            new_name = pair.skill_b if a_is_existing else pair.skill_a

            existing_skill = next(s for s in existing_skills if s.name == existing_name)
            new_skill = next(s for s in new_skills if s.name == new_name)

            merged = merge_skills(existing_skill, new_skill, provider)
            if merged:
                merged_results.append(merged)
                merged_new_names.add(new_name)

    # Novel skills are new skills that weren't merged
    novel_skills = [s for s in new_skills if s.name not in merged_new_names]

    return merged_results, novel_skills
