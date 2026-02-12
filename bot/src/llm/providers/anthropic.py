from __future__ import annotations

import json
import logging
import uuid

import anthropic

from llm.base import LLMProvider
from llm.types import ChatMessage, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: str, model: str | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    async def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        system_prompt, anthropic_messages = self._build_messages(messages)

        kwargs: dict = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        response = await self.client.messages.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _build_messages(
        messages: list[ChatMessage],
    ) -> tuple[str | None, list[dict]]:
        """Convert ChatMessages to Anthropic format, extracting system prompt."""
        system_prompt: str | None = None
        result: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue

            if msg.role == "user":
                result.append({"role": "user", "content": msg.content or ""})

            elif msg.role == "assistant":
                content: list[dict] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                result.append({"role": "assistant", "content": content})

            elif msg.role == "tool":
                # Anthropic expects tool results as user messages with tool_result blocks
                result.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "",
                            "content": msg.content or "",
                        }
                    ],
                })

        return system_prompt, result

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id or str(uuid.uuid4()),
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )
