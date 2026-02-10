"""paper2skills CLI - Generate AI agent skill files from research papers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__

app = typer.Typer(
    name="paper2skills",
    help="Generate AI agent skill files from research papers.",
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve_provider(provider: Optional[str], config_path: Optional[Path]) -> str:
    """Determine the LLM provider to use.

    Priority: explicit CLI flag > config file > auto-detect.
    Auto-detect: if a Copilot OAuth token exists, use 'copilot', else 'github'.
    """
    if provider is not None:
        return provider

    from .config import Config

    cfg = Config.load(config_path)

    # If the config file explicitly sets a provider (not default), use it
    if cfg.provider != "github":
        return cfg.provider

    # Auto-detect: check for Copilot OAuth token
    from .auth import get_copilot_oauth_token

    if get_copilot_oauth_token():
        return "copilot"

    return "github"


def _get_provider(
    provider: str,
    model: Optional[str],
    config_path: Optional[Path],
):
    """Instantiate the correct LLM provider."""
    from .config import Config

    cfg = Config.load(config_path)

    if provider == "github":
        from .providers.github import GithubModelsProvider

        if model:
            cfg.github.model = model
        return GithubModelsProvider(cfg.github)
    elif provider == "copilot":
        from .providers.copilot import CopilotProvider

        if model:
            cfg.copilot.model = model
        return CopilotProvider(cfg.copilot)
    elif provider == "openai":
        from .providers.openai_provider import OpenAIProvider

        if model:
            cfg.openai.model = model
        return OpenAIProvider(cfg.openai)
    elif provider == "litellm":
        from .providers.litellm_provider import LitellmProvider

        if model:
            cfg.litellm.model = model
        return LitellmProvider(cfg.litellm)
    else:
        typer.echo(f"Unknown provider: {provider}", err=True)
        raise typer.Exit(1)


def _get_config(config_path: Optional[Path]):
    from .config import Config

    return Config.load(config_path)


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------


@app.command()
def generate(
    sources: list[str] = typer.Argument(
        ...,
        help="Paper sources: PDF paths, arXiv IDs/URLs, DOIs, or text files",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider: 'github', 'copilot', 'openai', or 'litellm' (auto-detects if omitted)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override model name (e.g. 'openai/gpt-4o')",
    ),
    output_dir: Path = typer.Option(
        Path(".opencode/skills"),
        "--output-dir",
        "-o",
        help="Output directory for SKILL.md files",
    ),
    merge_into: Optional[Path] = typer.Option(
        None,
        "--merge-into",
        help="Existing skills directory to merge into (detects overlaps)",
    ),
    max_skills: int = typer.Option(
        5,
        "--max-skills",
        help="Max skills to extract per paper",
    ),
    evaluate: bool = typer.Option(
        True,
        "--evaluate/--no-evaluate",
        help="Evaluate generated skills after creation",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config.yaml",
    ),
):
    """Generate SKILL.md files from one or more research papers."""
    from .ingest.router import ingest_paper
    from .generate.generator import generate_skills
    from .output.opencode import write_skills, read_existing_skills
    from .evaluate.evaluator import evaluate_skills
    from .evaluate.merger import merge_into_existing, detect_overlaps

    provider = _resolve_provider(provider, config_path)
    llm = _get_provider(provider, model, config_path)

    console.print(
        Panel(
            f"[bold]paper2skills[/bold] v{__version__}\n"
            f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{llm.model_name}[/cyan]\n"
            f"Sources: {len(sources)} | Max skills/paper: {max_skills}",
            title="Generate",
        )
    )

    all_skills = []

    # Phase 1: Ingest and generate
    for i, source in enumerate(sources, 1):
        console.print(f"\n[bold]Paper {i}/{len(sources)}:[/bold] {source}")

        try:
            text, metadata = ingest_paper(source)
            console.print(f"  Title: [cyan]{metadata.get('title', 'Unknown')}[/cyan]")
            console.print(f"  Text length: {len(text):,} chars")

            skills = generate_skills(text, metadata, llm, max_skills)
            all_skills.extend(skills)

            for skill in skills:
                console.print(f"    [green]+[/green] {skill.name}: {skill.description}")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            continue

    if not all_skills:
        console.print("\n[red]No skills were generated.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Total skills generated: {len(all_skills)}[/bold]")

    # Phase 2: Merge into existing (if requested)
    if merge_into:
        console.print(f"\n[bold]Merging into:[/bold] {merge_into}")
        existing = read_existing_skills(merge_into)
        console.print(f"  Found {len(existing)} existing skills")

        if existing:
            merged, novel = merge_into_existing(all_skills, existing, llm)
            console.print(f"  Merged: {len(merged)} | Novel: {len(novel)}")

            # Write merged skills (overwrite existing)
            if merged:
                write_skills(merged, merge_into)
            # Write novel skills
            if novel:
                write_skills(novel, merge_into)

            all_skills = merged + novel
        else:
            # No existing skills, just write all
            write_skills(all_skills, merge_into)
    else:
        # Write to output directory
        write_skills(all_skills, output_dir)

    # Phase 3: Evaluate (if requested)
    if evaluate and all_skills:
        console.print("\n[bold]Evaluating generated skills...[/bold]")
        report = evaluate_skills(all_skills, llm)
        report.print_summary()

        # Check for overlaps within generated skills
        if len(all_skills) > 1:
            console.print("\n[bold]Checking for overlaps...[/bold]")
            overlap_report = detect_overlaps(all_skills, llm)
            overlap_report.print_summary()

    console.print(
        f"\n[green bold]Done![/green bold] Generated {len(all_skills)} skills."
    )


# ---------------------------------------------------------------------------
# evaluate command
# ---------------------------------------------------------------------------


@app.command(name="evaluate")
def evaluate_cmd(
    skills_dir: Path = typer.Argument(
        ...,
        help="Directory containing SKILL.md files to evaluate",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider: 'github', 'copilot', 'openai', or 'litellm' (auto-detects if omitted)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override model name",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write evaluation report to file (markdown)",
    ),
    check_overlaps: bool = typer.Option(
        True,
        "--overlaps/--no-overlaps",
        help="Check for overlapping skills",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config.yaml",
    ),
):
    """Evaluate existing SKILL.md files for quality and overlap."""
    from .output.opencode import read_existing_skills
    from .evaluate.evaluator import evaluate_skills
    from .evaluate.merger import detect_overlaps

    provider = _resolve_provider(provider, config_path)
    llm = _get_provider(provider, model, config_path)

    console.print(
        Panel(
            f"[bold]paper2skills[/bold] v{__version__}\n"
            f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{llm.model_name}[/cyan]\n"
            f"Skills directory: {skills_dir}",
            title="Evaluate",
        )
    )

    # Read existing skills
    skills = read_existing_skills(skills_dir)
    if not skills:
        console.print(f"[red]No SKILL.md files found in {skills_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"Found [cyan]{len(skills)}[/cyan] skills to evaluate\n")

    # Evaluate
    report = evaluate_skills(skills, llm)
    report.print_summary()

    # Check overlaps
    overlap_report = None
    if check_overlaps and len(skills) > 1:
        console.print("\n[bold]Checking for overlaps...[/bold]")
        overlap_report = detect_overlaps(skills, llm)
        overlap_report.print_summary()

    # Write report
    if output:
        report_text = report.to_markdown()
        if overlap_report:
            report_text += "\n\n" + overlap_report.to_markdown()
        output.write_text(report_text, encoding="utf-8")
        console.print(f"\nReport written to: [green]{output}[/green]")

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Keep: [green]{report.keep_count}[/green]")
    console.print(f"  Improve: [yellow]{report.improve_count}[/yellow]")
    console.print(f"  Discard: [red]{report.discard_count}[/red]")


# ---------------------------------------------------------------------------
# merge command
# ---------------------------------------------------------------------------


@app.command()
def merge(
    skills_dir: Path = typer.Argument(
        ...,
        help="Directory containing SKILL.md files to analyze and merge",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider (auto-detects if omitted)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override model name",
    ),
    auto_merge: bool = typer.Option(
        False,
        "--auto-merge",
        help="Automatically merge overlapping skills (otherwise just report)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write merge report to file",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config.yaml",
    ),
):
    """Detect overlapping skills and optionally merge them."""
    from .output.opencode import read_existing_skills, write_skills
    from .evaluate.merger import detect_overlaps, merge_skills as do_merge

    provider = _resolve_provider(provider, config_path)
    llm = _get_provider(provider, model, config_path)

    console.print(
        Panel(
            f"[bold]paper2skills[/bold] v{__version__}\n"
            f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{llm.model_name}[/cyan]\n"
            f"Skills directory: {skills_dir}\n"
            f"Auto-merge: {'yes' if auto_merge else 'no'}",
            title="Merge",
        )
    )

    skills = read_existing_skills(skills_dir)
    if len(skills) < 2:
        console.print("[yellow]Need at least 2 skills to check for overlaps[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [cyan]{len(skills)}[/cyan] skills\n")

    # Detect overlaps
    report = detect_overlaps(skills, llm)
    report.print_summary()

    if output:
        output.write_text(report.to_markdown(), encoding="utf-8")
        console.print(f"\nReport written to: [green]{output}[/green]")

    # Auto-merge if requested
    if auto_merge and report.merge_groups:
        console.print(
            f"\n[bold]Auto-merging {len(report.merge_groups)} groups...[/bold]"
        )

        skills_by_name = {s.name: s for s in skills}
        merged_names: set[str] = set()

        for group in report.merge_groups:
            group_skills = [
                skills_by_name[name] for name in group if name in skills_by_name
            ]
            if len(group_skills) < 2:
                continue

            # Merge pairs sequentially
            result = group_skills[0]
            for other in group_skills[1:]:
                merged = do_merge(result, other, llm)
                if merged:
                    result = merged
                    merged_names.update(group)

            if result:
                write_skills([result], skills_dir)

                # Remove old skill directories
                for name in group:
                    if name != result.name:
                        old_dir = skills_dir / name
                        if old_dir.exists():
                            import shutil

                            shutil.rmtree(old_dir)
                            console.print(f"  Removed: [red]{old_dir}[/red]")

        console.print(
            f"\n[green bold]Done![/green bold] "
            f"Merged {len(merged_names)} skills into "
            f"{len(report.merge_groups)} consolidated skills."
        )


# ---------------------------------------------------------------------------
# models command
# ---------------------------------------------------------------------------


@app.command()
def models(
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider to list models for (auto-detects if not specified)",
    ),
):
    """List available models for a provider."""
    # Resolve provider using shared auto-detect logic
    provider = _resolve_provider(provider, None)

    if provider == "github":
        console.print("[bold]GitHub Models[/bold] (models.github.ai)")
        console.print("Popular models available:")
        model_list = [
            ("openai/gpt-4o", "GPT-4o - fast, high quality (default)"),
            ("openai/gpt-4o-mini", "GPT-4o Mini - cheaper, faster"),
            ("openai/gpt-4.1", "GPT-4.1 - latest"),
            ("openai/o3-mini", "o3 Mini - reasoning model"),
            ("deepseek/DeepSeek-R1", "DeepSeek R1 - reasoning"),
            ("xai/grok-3-mini", "Grok 3 Mini"),
        ]
        for model_id, desc in model_list:
            console.print(f"  [cyan]{model_id}[/cyan] - {desc}")
        console.print("\nFull catalog: https://github.com/marketplace/models")
    elif provider == "copilot":
        console.print("[bold]GitHub Copilot[/bold] (api.githubcopilot.com)\n")

        # Try to fetch live model list
        try:
            from .config import Config

            cfg = Config.load()
            from .providers.copilot import CopilotProvider

            cp = CopilotProvider(cfg.copilot)
            live_models = cp.list_models()

            if live_models:
                console.print(f"Available models ({len(live_models)}):\n")
                for m in sorted(live_models, key=lambda x: x["id"]):
                    model_id = m["id"]
                    name = m.get("name", "")
                    version = m.get("version", "")

                    # Mark the default
                    suffix = ""
                    if model_id == cfg.copilot.model:
                        suffix = " [green](current default)[/green]"

                    detail = ""
                    if name and name != model_id:
                        detail = f" - {name}"
                    if version:
                        detail += f" (v{version})"

                    console.print(f"  [cyan]{model_id}[/cyan]{detail}{suffix}")

                console.print(
                    f"\nUse with: paper2skills generate ... --provider copilot -m [cyan]MODEL_ID[/cyan]"
                )
            else:
                console.print("[yellow]No models returned from API.[/yellow]")
                _print_copilot_fallback_list()

        except Exception as e:
            console.print(f"[yellow]Could not fetch live models: {e}[/yellow]\n")
            _print_copilot_fallback_list()

        console.print(
            "\n[dim]Embedding model: text-embedding-3-small (used for overlap detection).[/dim]"
        )
    elif provider == "openai":
        console.print("[bold]OpenAI[/bold] (api.openai.com)")
        console.print("Popular models:")
        model_list = [
            ("gpt-4o", "GPT-4o - fast, high quality (default)"),
            ("gpt-4o-mini", "GPT-4o Mini - cheaper, faster"),
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gpt-4.1", "GPT-4.1 - latest"),
            ("o3-mini", "o3 Mini - reasoning model"),
        ]
        for model_id, desc in model_list:
            console.print(f"  [cyan]{model_id}[/cyan] - {desc}")
        console.print(
            "\nEmbedding models: text-embedding-3-small (default), text-embedding-3-large"
        )
        console.print("Full list: https://platform.openai.com/docs/models")
    elif provider == "litellm":
        console.print("[bold]LiteLLM[/bold] - supports 100+ providers")
        console.print("Examples:")
        examples = [
            ("claude-sonnet-4-20250514", "Anthropic Claude Sonnet"),
            ("gpt-4o", "OpenAI GPT-4o (direct)"),
            ("ollama/llama3", "Local Ollama - Llama 3"),
            ("ollama/mistral", "Local Ollama - Mistral"),
        ]
        for model_id, desc in examples:
            console.print(f"  [cyan]{model_id}[/cyan] - {desc}")
        console.print("\nFull list: https://docs.litellm.ai/docs/providers")
    else:
        console.print(f"[red]Unknown provider: {provider}[/red]")


def _print_copilot_fallback_list():
    """Print a static fallback list of common Copilot models."""
    console.print("Common models (may vary by plan):")
    model_list = [
        ("gpt-4o", "GPT-4o (default)"),
        ("gpt-4o-mini", "GPT-4o Mini - faster"),
        ("gpt-4.1", "GPT-4.1 - latest"),
        ("claude-3.5-sonnet", "Claude 3.5 Sonnet"),
        ("claude-sonnet-4", "Claude Sonnet 4"),
        ("o3-mini", "o3 Mini - reasoning"),
    ]
    for model_id, desc in model_list:
        console.print(f"  [cyan]{model_id}[/cyan] - {desc}")


# ---------------------------------------------------------------------------
# login / logout commands
# ---------------------------------------------------------------------------


@app.command()
def login():
    """Authenticate with GitHub Copilot via browser (device flow).

    Opens your browser for GitHub authorization. The OAuth token is stored
    at ~/.config/paper2skills/copilot_token.json and used automatically
    by --provider copilot.
    """
    from .auth import device_flow_login

    device_flow_login()


@app.command()
def logout():
    """Remove stored Copilot authentication token."""
    from .auth import logout as do_logout, TOKEN_FILE

    if do_logout():
        console.print(f"[green]Removed stored token:[/green] {TOKEN_FILE}")
    else:
        console.print("[yellow]No stored token found.[/yellow]")


@app.command()
def status():
    """Show authentication status for all providers."""
    import os
    from .auth import (
        get_copilot_oauth_token,
        TOKEN_FILE,
        _read_stored_token,
        _read_vscode_token,
    )

    console.print("[bold]Authentication Status[/bold]\n")

    # GitHub Models
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if gh_token:
        prefix = gh_token[:7] + "..." if len(gh_token) > 10 else "***"
        console.print(f"  [green]github[/green]   GITHUB_TOKEN set ({prefix})")
    else:
        console.print(f"  [red]github[/red]   GITHUB_TOKEN not set")

    # Copilot
    stored = _read_stored_token()
    vscode = _read_vscode_token() if not stored else None
    copilot_env = os.environ.get("GITHUB_COPILOT_TOKEN", "")

    if stored:
        console.print(f"  [green]copilot[/green]  Logged in (token at {TOKEN_FILE})")
    elif vscode:
        console.print(f"  [green]copilot[/green]  Found VS Code Copilot token")
    elif copilot_env:
        console.print(f"  [green]copilot[/green]  GITHUB_COPILOT_TOKEN set")
    else:
        console.print(
            f"  [red]copilot[/red]  Not authenticated. Run: paper2skills login"
        )

    # OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        prefix = openai_key[:7] + "..." if len(openai_key) > 10 else "***"
        console.print(f"  [green]openai[/green]   OPENAI_API_KEY set ({prefix})")
    else:
        console.print(f"  [red]openai[/red]   OPENAI_API_KEY not set")

    # LiteLLM
    console.print(f"  [dim]litellm[/dim]  Varies by model (check litellm docs)")


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------


@app.command()
def version():
    """Show version information."""
    console.print(f"paper2skills v{__version__}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    app()


if __name__ == "__main__":
    main()
