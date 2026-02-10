"""OpenAI direct provider - uses api.openai.com."""

from __future__ import annotations

import time

from openai import OpenAI, RateLimitError, APIError
from rich.console import Console

from .base import BaseLLMProvider, LLMResponse
from ..config import OpenAIConfig

console = Console(stderr=True)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using OpenAI's API directly."""

    def __init__(self, config: OpenAIConfig):
        self._config = config
        self._client = OpenAI(api_key=config.api_key)
        self._model = config.model
        self._embedding_model = config.embedding_model

    @property
    def model_name(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion with retry on rate limits."""
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
                wait = 2 ** (attempt + 1) * 5
                console.print(
                    f"[yellow]Rate limited. Waiting {wait}s "
                    f"({attempt + 1}/{max_retries})...[/yellow]"
                )
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise
            except APIError as e:
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
        """Get embeddings via OpenAI."""
        response = self._client.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
