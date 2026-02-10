"""GitHub Copilot provider - uses the Copilot internal API.

This provider works with GitHub Copilot subscriptions by using the same
token exchange flow that VS Code uses. It requires a Copilot OAuth token
(obtained via 'paper2skills login' or read from VS Code's config).

The flow is:
1. Get OAuth token (ghu_xxx) via auto-detection
2. Exchange it for a short-lived Copilot session token
3. Use that session token against the Copilot API endpoint
"""

from __future__ import annotations

import time
from typing import Optional

import requests
from openai import OpenAI, RateLimitError, APIError
from rich.console import Console

from .base import BaseLLMProvider, LLMResponse
from ..config import CopilotConfig

console = Console(stderr=True)

# Copilot token exchange and API endpoints
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_CHAT_URL = "https://api.githubcopilot.com"


class CopilotProvider(BaseLLMProvider):
    """LLM provider using GitHub Copilot's API via token exchange.

    Requires a Copilot OAuth token (ghu_xxx). Get one by running
    'paper2skills login' or having VS Code with Copilot installed.
    """

    def __init__(self, config: CopilotConfig):
        self._config = config
        self._oauth_token = config.token  # OAuth token (ghu_xxx)
        self._model = config.model
        self._embedding_model = config.embedding_model
        self._copilot_token: Optional[str] = None
        self._token_expires: float = 0
        self._client: Optional[OpenAI] = None

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_token(self) -> None:
        """Exchange OAuth token for Copilot session token if needed."""
        if self._copilot_token and time.time() < self._token_expires - 60:
            return

        console.print("  [dim]Exchanging token for Copilot session...[/dim]")

        # Match OpenCode/VS Code: Bearer auth + editor headers for token exchange
        headers = {
            "Authorization": f"Bearer {self._oauth_token}",
            "Accept": "application/json",
            "User-Agent": "GitHubCopilotChat/0.35.0",
            "Editor-Version": "vscode/1.107.0",
            "Editor-Plugin-Version": "copilot-chat/0.35.0",
            "Copilot-Integration-Id": "vscode-chat",
        }

        resp = requests.get(COPILOT_TOKEN_URL, headers=headers, timeout=30)

        if resp.status_code == 401:
            raise EnvironmentError(
                "Copilot token rejected (401). Your OAuth token may have "
                "expired. Run 'paper2skills login' to re-authenticate."
            )
        if resp.status_code == 403:
            body = ""
            try:
                body = resp.text[:500]
            except Exception:
                pass
            raise EnvironmentError(
                f"Copilot access denied (403). Your GitHub account may not "
                f"have an active Copilot subscription, or the OAuth token "
                f"lacks the required permissions.\n"
                f"  Response: {body}\n"
                f"  Try: paper2skills logout && paper2skills login"
            )
        if resp.status_code == 404:
            raise EnvironmentError(
                "Copilot token exchange failed (404). This usually means "
                "you're using a PAT (ghp_xxx) instead of a Copilot OAuth "
                "token (ghu_xxx). Run 'paper2skills login' to get the "
                "correct token type."
            )

        resp.raise_for_status()
        data = resp.json()

        self._copilot_token = data.get("token")
        self._token_expires = data.get("expires_at", time.time() + 1800)

        if not self._copilot_token:
            raise EnvironmentError(
                "Failed to get Copilot session token. Response: " + str(data)
            )

        # Create OpenAI client pointing at Copilot endpoint
        self._client = OpenAI(
            base_url=COPILOT_CHAT_URL,
            api_key=self._copilot_token,
            default_headers={
                "User-Agent": "GitHubCopilotChat/0.35.0",
                "Editor-Version": "vscode/1.107.0",
                "Editor-Plugin-Version": "copilot-chat/0.35.0",
                "Copilot-Integration-Id": "vscode-chat",
                "Openai-Intent": "conversation-edits",
            },
        )

        console.print("  [dim]Copilot session established.[/dim]")

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion via Copilot."""
        self._ensure_token()
        assert self._client is not None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model or self._model,
                    usage=(
                        {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens,
                        }
                        if response.usage
                        else None
                    ),
                )
            except RateLimitError:
                wait = 2 ** (attempt + 1) * 10
                console.print(
                    f"[yellow]Rate limited. Waiting {wait}s "
                    f"({attempt + 1}/{max_retries})...[/yellow]"
                )
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise
            except APIError as e:
                if e.status_code == 401:
                    # Session token may have expired, re-exchange
                    console.print(
                        "[yellow]Copilot session expired, re-authenticating...[/yellow]"
                    )
                    self._copilot_token = None
                    self._ensure_token()
                    continue
                if attempt < max_retries - 1 and e.status_code and e.status_code >= 500:
                    wait = 2 ** (attempt + 1) * 5
                    console.print(
                        f"[yellow]API error ({e.status_code}). Retrying in {wait}s...[/yellow]"
                    )
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError("Max retries exceeded")

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings via Copilot API (text-embedding-3-small)."""
        self._ensure_token()
        assert self._client is not None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except RateLimitError:
                wait = 2 ** (attempt + 1) * 10
                console.print(
                    f"[yellow]Embedding rate limited. Waiting {wait}s...[/yellow]"
                )
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise
            except APIError as e:
                if e.status_code == 401:
                    # Session token may have expired
                    console.print(
                        "[yellow]Copilot session expired, re-authenticating...[/yellow]"
                    )
                    self._copilot_token = None
                    self._ensure_token()
                    continue
                raise

        raise RuntimeError("Max retries exceeded")

    def list_models(self) -> list[dict[str, str]]:
        """Fetch available models from the Copilot API.

        Returns a list of dicts with 'id', 'name', and 'version' keys.
        """
        self._ensure_token()

        headers = {
            "Authorization": f"Bearer {self._copilot_token}",
            "Accept": "application/json",
            "User-Agent": "GitHubCopilotChat/0.35.0",
            "Editor-Version": "vscode/1.107.0",
            "Editor-Plugin-Version": "copilot-chat/0.35.0",
            "Copilot-Integration-Id": "vscode-chat",
        }

        resp = requests.get(
            f"{COPILOT_CHAT_URL}/models",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        models = []
        for item in data.get("data", data if isinstance(data, list) else []):
            if isinstance(item, dict):
                models.append(
                    {
                        "id": item.get("id", item.get("model", "")),
                        "name": item.get("name", item.get("id", "")),
                        "version": item.get("version", ""),
                    }
                )

        return models
