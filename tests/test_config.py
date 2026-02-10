"""Tests for configuration loading."""

from pathlib import Path
import tempfile

import yaml

from paper2skills.config import Config, CopilotConfig, GithubConfig


class TestConfigDefaults:
    def test_default_provider(self):
        cfg = Config()
        assert cfg.provider == "github"

    def test_default_github_model(self):
        cfg = Config()
        assert cfg.github.model == "openai/gpt-4o"

    def test_default_copilot_model(self):
        cfg = Config()
        assert cfg.copilot.model == "gpt-4o"

    def test_default_copilot_embedding_model(self):
        cfg = Config()
        assert cfg.copilot.embedding_model == "text-embedding-3-small"

    def test_default_generation_settings(self):
        cfg = Config()
        assert cfg.generation.max_skills_per_paper == 5
        assert cfg.generation.max_body_lines == 300

    def test_default_evaluation_settings(self):
        cfg = Config()
        assert cfg.evaluation.min_score == 5.0
        assert cfg.evaluation.overlap_threshold == 0.7


class TestConfigLoad:
    def test_load_no_file_returns_defaults(self):
        cfg = Config.load(Path("/nonexistent/path/config.yaml"))
        assert cfg.provider == "github"
        assert cfg.github.model == "openai/gpt-4o"

    def test_load_from_yaml(self):
        data = {
            "provider": "copilot",
            "copilot": {
                "model": "claude-sonnet-4",
                "embedding_model": "text-embedding-3-large",
            },
            "generation": {
                "max_skills_per_paper": 10,
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            cfg = Config.load(Path(f.name))

        assert cfg.provider == "copilot"
        assert cfg.copilot.model == "claude-sonnet-4"
        assert cfg.copilot.embedding_model == "text-embedding-3-large"
        assert cfg.generation.max_skills_per_paper == 10
        # Unspecified fields retain defaults
        assert cfg.github.model == "openai/gpt-4o"
        assert cfg.evaluation.min_score == 5.0

    def test_load_partial_config(self):
        """Config with only some sections should leave others as defaults."""
        data = {"provider": "openai"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            cfg = Config.load(Path(f.name))

        assert cfg.provider == "openai"
        assert cfg.copilot.model == "gpt-4o"

    def test_from_dict_all_sections(self):
        data = {
            "provider": "litellm",
            "github": {"model": "custom-model", "embedding_model": "custom-embed"},
            "copilot": {"model": "gpt-5"},
            "openai": {"model": "gpt-4-turbo"},
            "litellm": {"model": "claude-sonnet-4-20250514"},
            "generation": {"max_skills_per_paper": 3, "max_body_lines": 100},
            "evaluation": {"min_score": 7.0, "overlap_threshold": 0.8},
            "output": {"format": "opencode", "directory": "custom/path"},
        }
        cfg = Config._from_dict(data)
        assert cfg.provider == "litellm"
        assert cfg.github.model == "custom-model"
        assert cfg.github.embedding_model == "custom-embed"
        assert cfg.copilot.model == "gpt-5"
        assert cfg.openai.model == "gpt-4-turbo"
        assert cfg.litellm.model == "claude-sonnet-4-20250514"
        assert cfg.generation.max_skills_per_paper == 3
        assert cfg.evaluation.overlap_threshold == 0.8
        assert cfg.output.directory == "custom/path"
