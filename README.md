# paper2skills

Extract structured, reusable skill files from research papers using LLMs.

`paper2skills` reads a research paper (from arXiv, DOI, PDF, or plain text), uses a large language model to identify the key actionable techniques, and outputs them as [OpenCode](https://opencode.ai)-compatible `SKILL.md` files that AI coding agents can use.

## Features

- **Multiple input sources** — arXiv IDs/URLs, DOIs, local PDFs, plain text/markdown
- **4 LLM providers** — GitHub Copilot, GitHub Models API, OpenAI, and LiteLLM (100+ backends)
- **Zero-config with Copilot** — authenticate with `paper2skills login` and use your existing GitHub Copilot subscription
- **Skill evaluation** — scores generated skills on actionability, specificity, conciseness, novelty, and correctness
- **Overlap detection & merging** — finds duplicate/overlapping skills using embeddings + LLM analysis and merges them
- **OpenCode SKILL.md format** — structured YAML frontmatter + markdown body, ready for AI agent consumption

## Installation

```bash
pip install paper2skills
```

With LiteLLM support (for Anthropic, Ollama, and 100+ other providers):

```bash
pip install "paper2skills[litellm]"
```

### Requirements

- Python 3.10+
- An LLM provider (see [Provider Setup](#provider-setup))

## Quick Start

### 1. Authenticate (recommended: GitHub Copilot)

```bash
paper2skills login
```

This opens your browser for GitHub OAuth. Once authorized, your Copilot subscription is used automatically — no API keys needed.

### 2. Generate skills from a paper

```bash
# From an arXiv paper
paper2skills generate "arxiv:1706.03762"

# From a DOI
paper2skills generate "10.1038/s41586-021-03819-2"

# From a local PDF
paper2skills generate ./my-paper.pdf

# Multiple papers at once
paper2skills generate "arxiv:1706.03762" "arxiv:2005.14165" ./local-paper.pdf
```

Skills are written to `.opencode/skills/` by default:

```
.opencode/skills/
  scaled-dot-product-attention/
    SKILL.md
  multi-head-attention/
    SKILL.md
```

### 3. Evaluate and merge

```bash
# Evaluate skill quality
paper2skills evaluate .opencode/skills/

# Detect overlaps and auto-merge
paper2skills merge .opencode/skills/ --auto-merge
```

## Commands

| Command | Description |
|---------|-------------|
| `generate` | Extract skills from one or more research papers |
| `evaluate` | Score existing skills for quality (1-10 on 5 criteria) |
| `merge` | Detect overlapping skills and optionally merge them |
| `models` | List available models for the active provider |
| `login` | Authenticate with GitHub Copilot (browser-based OAuth) |
| `logout` | Remove stored Copilot authentication token |
| `status` | Show authentication status for all providers |
| `version` | Show version information |

### Common options

```bash
# Use a specific provider
paper2skills generate "arxiv:1706.03762" --provider openai

# Use a specific model
paper2skills generate "arxiv:1706.03762" -m claude-sonnet-4

# Custom output directory
paper2skills generate "arxiv:1706.03762" -o ./my-skills/

# Limit number of skills per paper
paper2skills generate "arxiv:1706.03762" --max-skills 3

# Skip evaluation after generation
paper2skills generate "arxiv:1706.03762" --no-evaluate

# Merge new skills into an existing directory
paper2skills generate "arxiv:2005.14165" --merge-into .opencode/skills/
```

## Provider Setup

The provider is auto-detected: if you're logged in to Copilot, it uses Copilot. Otherwise, it falls back to GitHub Models API. You can always override with `--provider`.

### GitHub Copilot (recommended)

Uses your existing Copilot subscription. No extra cost.

```bash
paper2skills login          # One-time browser auth
paper2skills models         # See available models (gpt-4o, claude-sonnet-4, etc.)
paper2skills generate "arxiv:1706.03762"
```

### GitHub Models API

Free tier with a GitHub PAT.

```bash
export GITHUB_TOKEN="ghp_your_pat_here"   # Needs 'models:read' scope
paper2skills generate "arxiv:1706.03762" --provider github
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
paper2skills generate "arxiv:1706.03762" --provider openai
```

### LiteLLM

Supports Anthropic, Ollama, Azure, Bedrock, and [100+ more](https://docs.litellm.ai/docs/providers).

```bash
pip install "paper2skills[litellm]"
export ANTHROPIC_API_KEY="sk-ant-..."
paper2skills generate "arxiv:1706.03762" --provider litellm -m claude-sonnet-4-20250514
```

## Configuration

Create a `config.yaml` (or `paper2skills.yaml`) in your working directory or at `~/.config/paper2skills/config.yaml`:

```yaml
provider: copilot

copilot:
  model: gpt-4o
  embedding_model: text-embedding-3-small

github:
  model: openai/gpt-4o
  token_env: GITHUB_TOKEN
  embedding_model: openai/text-embedding-3-small

generation:
  max_skills_per_paper: 5
  max_body_lines: 300

evaluation:
  min_score: 5.0
  overlap_threshold: 0.7
```

See [`config.example.yaml`](config.example.yaml) for all options.

## SKILL.md Format

Each skill is a directory containing a `SKILL.md` file with YAML frontmatter and a markdown body:

```markdown
---
name: scaled-dot-product-attention
description: Implement efficient self-attention using scaled dot products
metadata:
  source-paper: "Attention Is All You Need"
  arxiv-id: "1706.03762"
---

## When to use

Use when building sequence models that need to relate
different positions in the input...

## Instructions

1. Compute attention scores...
2. Scale by square root of key dimension...

## Examples

...

## Pitfalls

...
```

Skills follow the [OpenCode](https://opencode.ai) skill format and are designed to be consumed by AI coding agents.

## Development

```bash
git clone https://github.com/kiryteo/paper2skills-cli.git
cd paper2skills-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
