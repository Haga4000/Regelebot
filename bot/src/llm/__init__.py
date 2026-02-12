from __future__ import annotations

import logging

from llm.base import LLMProvider
from llm.types import ChatMessage, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


def create_llm_provider() -> LLMProvider:
    """Factory: create the LLM provider specified by config.

    Only the selected provider's SDK needs to be installed.
    """
    from config import settings

    provider = settings.LLM_PROVIDER.lower()
    api_key = settings.LLM_API_KEY
    model = settings.LLM_MODEL or None
    base_url = settings.LLM_BASE_URL

    if provider == "gemini":
        from llm.providers.gemini import GeminiProvider

        instance = GeminiProvider(api_key=api_key, model=model)

    elif provider == "mistral":
        from llm.providers.mistral import MistralProvider

        instance = MistralProvider(api_key=api_key, model=model)

    elif provider == "openai":
        from llm.providers.openai import OpenAIProvider

        instance = OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

    elif provider == "anthropic":
        from llm.providers.anthropic import AnthropicProvider

        instance = AnthropicProvider(api_key=api_key, model=model)

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            "Supported: gemini, mistral, openai, anthropic"
        )

    extra = f" via {base_url}" if base_url else ""
    logger.info("LLM provider: %s | model: %s%s", provider, instance.model, extra)
    return instance


__all__ = [
    "ChatMessage",
    "LLMProvider",
    "LLMResponse",
    "ToolCall",
    "ToolDefinition",
    "create_llm_provider",
]
