"""Configuration loading and management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class GithubConfig:
    model: str = "openai/gpt-4o"
    token_env: str = "GITHUB_TOKEN"
    embedding_model: str = "openai/text-embedding-3-small"

    @property
    def token(self) -> str:
        token = os.environ.get(self.token_env, "")
        if not token:
            raise EnvironmentError(
                f"Environment variable '{self.token_env}' is not set. "
                "Set it to a GitHub PAT with 'models:read' scope."
            )
        return token


@dataclass
class CopilotConfig:
    model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    @property
    def token(self) -> str:
        """Get Copilot OAuth token from auto-detection.

        Search order: stored token > VS Code config > GITHUB_COPILOT_TOKEN env var.
        If nothing found, tells user to run 'paper2skills login'.
        """
        from .auth import get_copilot_oauth_token

        token = get_copilot_oauth_token()
        if not token:
            raise EnvironmentError(
                "No Copilot OAuth token found. Run 'paper2skills login' to "
                "authenticate with GitHub Copilot, or set GITHUB_COPILOT_TOKEN."
            )
        return token


@dataclass
class OpenAIConfig:
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    embedding_model: str = "text-embedding-3-small"

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise EnvironmentError(
                f"Environment variable '{self.api_key_env}' is not set."
            )
        return key


@dataclass
class LitellmConfig:
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    embedding_model: str = "text-embedding-3-small"

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise EnvironmentError(
                f"Environment variable '{self.api_key_env}' is not set."
            )
        return key


@dataclass
class GenerationConfig:
    max_skills_per_paper: int = 5
    max_body_lines: int = 300


@dataclass
class EvaluationConfig:
    min_score: float = 5.0
    overlap_threshold: float = 0.7


@dataclass
class OutputConfig:
    format: str = "opencode"
    directory: str = ".opencode/skills"


@dataclass
class Config:
    provider: str = "github"
    audience: str = ""
    github: GithubConfig = field(default_factory=GithubConfig)
    copilot: CopilotConfig = field(default_factory=CopilotConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    litellm: LitellmConfig = field(default_factory=LitellmConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Config:
        """Load config from YAML file, falling back to defaults."""
        if path is None:
            # Search for config in current dir, then home dir
            candidates = [
                Path.cwd() / "paper2skills.yaml",
                Path.cwd() / "config.yaml",
                Path.home() / ".config" / "paper2skills" / "config.yaml",
            ]
            for candidate in candidates:
                if candidate.exists():
                    path = candidate
                    break

        if path is not None and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls._from_dict(data)

        return cls()

    @classmethod
    def _from_dict(cls, data: dict) -> Config:
        cfg = cls()
        cfg.provider = data.get("provider", cfg.provider)
        cfg.audience = data.get("audience", cfg.audience)

        if "github" in data:
            gh = data["github"]
            cfg.github = GithubConfig(
                model=gh.get("model", cfg.github.model),
                token_env=gh.get("token_env", cfg.github.token_env),
                embedding_model=gh.get("embedding_model", cfg.github.embedding_model),
            )

        if "litellm" in data:
            lt = data["litellm"]
            cfg.litellm = LitellmConfig(
                model=lt.get("model", cfg.litellm.model),
                api_key_env=lt.get("api_key_env", cfg.litellm.api_key_env),
                embedding_model=lt.get("embedding_model", cfg.litellm.embedding_model),
            )

        if "copilot" in data:
            cp = data["copilot"]
            cfg.copilot = CopilotConfig(
                model=cp.get("model", cfg.copilot.model),
                embedding_model=cp.get("embedding_model", cfg.copilot.embedding_model),
            )

        if "openai" in data:
            oa = data["openai"]
            cfg.openai = OpenAIConfig(
                model=oa.get("model", cfg.openai.model),
                api_key_env=oa.get("api_key_env", cfg.openai.api_key_env),
                embedding_model=oa.get("embedding_model", cfg.openai.embedding_model),
            )

        if "generation" in data:
            gen = data["generation"]
            cfg.generation = GenerationConfig(
                max_skills_per_paper=gen.get(
                    "max_skills_per_paper", cfg.generation.max_skills_per_paper
                ),
                max_body_lines=gen.get("max_body_lines", cfg.generation.max_body_lines),
            )

        if "evaluation" in data:
            ev = data["evaluation"]
            cfg.evaluation = EvaluationConfig(
                min_score=ev.get("min_score", cfg.evaluation.min_score),
                overlap_threshold=ev.get(
                    "overlap_threshold", cfg.evaluation.overlap_threshold
                ),
            )

        if "output" in data:
            out = data["output"]
            cfg.output = OutputConfig(
                format=out.get("format", cfg.output.format),
                directory=out.get("directory", cfg.output.directory),
            )

        return cfg
