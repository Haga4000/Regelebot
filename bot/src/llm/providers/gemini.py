from __future__ import annotations

import logging
import uuid
from typing import Any

from google import genai
from google.genai import types

from llm.base import LLMProvider
from llm.types import ChatMessage, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    DEFAULT_MODEL = "gemini-2.5-flash-lite"

    def __init__(self, api_key: str, model: str | None = None):
        self.client = genai.Client(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    async def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        system_instruction, contents = self._build_contents(messages)

        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = [self._build_tools(tools)]

        config = types.GenerateContentConfig(**config_kwargs)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return self._parse_response(response)

    def _build_contents(
        self, messages: list[ChatMessage]
    ) -> tuple[str | None, list[types.Content]]:
        """Convert ChatMessages to Gemini format, extracting system prompt."""
        system_instruction: str | None = None
        contents: list[types.Content] = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
                continue

            if msg.role == "tool":
                # Tool results are sent as user role with function response parts
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg.tool_name or "",
                                response={"result": msg.content},
                            )
                        ],
                    )
                )
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # Assistant message with tool calls
                    parts = []
                    if msg.content:
                        parts.append(types.Part.from_text(text=msg.content))
                    for tc in msg.tool_calls:
                        parts.append(
                            types.Part.from_function_call(
                                name=tc.name, args=tc.arguments
                            )
                        )
                    contents.append(types.Content(role="model", parts=parts))
                else:
                    contents.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=msg.content or "")],
                        )
                    )
            else:
                # user role
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg.content or "")],
                    )
                )

        # Gemini requires strict user/model alternation
        contents = self._consolidate_contents(contents)
        return system_instruction, contents

    @staticmethod
    def _build_tools(tools: list[ToolDefinition]) -> types.Tool:
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=t.parameters,
                )
                for t in tools
            ]
        )

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        if not response.candidates or not response.candidates[0].content.parts:
            return LLMResponse()

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for part in response.candidates[0].content.parts:
            if part.function_call:
                tool_calls.append(
                    ToolCall(
                        id=str(uuid.uuid4()),
                        name=part.function_call.name,
                        arguments=dict(part.function_call.args)
                        if part.function_call.args
                        else {},
                    )
                )
            elif part.text:
                text_parts.append(part.text)

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _consolidate_contents(
        contents: list[types.Content],
    ) -> list[types.Content]:
        """Merge consecutive same-role entries for Gemini's strict alternation."""
        if not contents:
            return contents

        consolidated: list[types.Content] = [contents[0]]
        for entry in contents[1:]:
            if entry.role == consolidated[-1].role:
                consolidated[-1].parts.extend(entry.parts)
            else:
                consolidated.append(entry)
        return consolidated
