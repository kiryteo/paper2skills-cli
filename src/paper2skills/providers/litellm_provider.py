"""LiteLLM provider for multi-provider LLM support."""

from __future__ import annotations

import os
from typing import Optional

from .base import BaseLLMProvider, LLMResponse
from ..config import LitellmConfig


class LitellmProvider(BaseLLMProvider):
    """LLM provider using LiteLLM for multi-provider support.

    Supports OpenAI, Anthropic, Ollama, and 100+ other providers.
    Requires `pip install paper2skills[litellm]`.
    """

    def __init__(self, config: LitellmConfig):
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "LiteLLM is not installed. Install with: "
                "pip install paper2skills[litellm]"
            )

        self._config = config
        self._model = config.model
        self._embedding_model = config.embedding_model
        self._litellm = litellm

        # Set the API key in the environment if not already set
        # LiteLLM reads from standard env vars (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
        if config.api_key_env:
            key = os.environ.get(config.api_key_env, "")
            if not key:
                raise EnvironmentError(
                    f"Environment variable '{config.api_key_env}' is not set."
                )

    @property
    def model_name(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion via LiteLLM."""
        response = self._litellm.completion(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return LLMResponse(content=content, model=self._model, usage=usage)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings via LiteLLM."""
        response = self._litellm.embedding(
            model=self._embedding_model,
            input=texts,
        )
        return [item["embedding"] for item in response.data]
