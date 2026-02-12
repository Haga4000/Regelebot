from __future__ import annotations

import logging
import uuid

from openai import AsyncOpenAI

from llm.base import LLMProvider
from llm.types import ChatMessage, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider. Also works with Ollama via base_url."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
    ):
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)
        self.model = model or self.DEFAULT_MODEL

    async def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        openai_messages = self._build_messages(messages)

        kwargs: dict = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _build_messages(messages: list[ChatMessage]) -> list[dict]:
        result = []
        for msg in messages:
            if msg.role == "system":
                result.append({"role": "system", "content": msg.content})
            elif msg.role == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                entry: dict = {"role": "assistant"}
                if msg.content:
                    entry["content"] = msg.content
                if msg.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": _serialize_args(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                    if not msg.content:
                        entry["content"] = None
                result.append(entry)
            elif msg.role == "tool":
                result.append({
                    "role": "tool",
                    "content": msg.content or "",
                    "tool_call_id": msg.tool_call_id or "",
                })
        return result

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id or str(uuid.uuid4()),
                        name=tc.function.name,
                        arguments=_parse_args(tc.function.arguments),
                    )
                )

        return LLMResponse(
            content=message.content if message.content else None,
            tool_calls=tool_calls,
        )


def _serialize_args(args: dict) -> str:
    import json
    return json.dumps(args)


def _parse_args(args_str: str | dict) -> dict:
    if isinstance(args_str, dict):
        return args_str
    import json
    try:
        return json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        return {}
