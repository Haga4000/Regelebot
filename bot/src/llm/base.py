from __future__ import annotations

from abc import ABC, abstractmethod

from llm.types import ChatMessage, LLMResponse, ToolDefinition


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        ...

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Convenience method for simple text generation (no tools)."""
        response = await self.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content or ""
