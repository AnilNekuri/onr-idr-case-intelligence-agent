"""Amazon Bedrock Mantle language model and client-side tool orchestration."""

import json
from typing import Any

from anthropic import AnthropicBedrockMantle, AnthropicError
from botocore.exceptions import BotoCoreError  # type: ignore[import-untyped]
from openai import OpenAI, OpenAIError
from openai.providers import bedrock

from app.language_models.language_model import (
    LanguageModelError,
    ToolCallingResult,
    ToolCallRecord,
    ToolDefinition,
    ToolExecutor,
)


class BedrockMantleLanguageModel:
    """Generate text through the model's supported Bedrock Mantle API."""

    def __init__(
        self,
        model_id: str,
        *,
        region_name: str,
        profile_name: str | None = None,
        max_output_tokens: int = 512,
        client: Any | None = None,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        if not region_name.strip():
            raise ValueError("region_name must not be empty")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be at least 1")

        self._uses_anthropic_messages = model_id.startswith("anthropic.")
        self._uses_openai_responses = model_id.startswith("openai.")
        if client is None:
            if self._uses_anthropic_messages:
                client = AnthropicBedrockMantle(
                    aws_region=region_name,
                    aws_profile=profile_name,
                )
            else:
                base_url = self._mantle_base_url(model_id, region_name)
                provider = (
                    bedrock(
                        region=region_name,
                        profile=profile_name,
                        base_url=base_url,
                    )
                    if profile_name is not None
                    else bedrock(region=region_name, base_url=base_url)
                )
                client = OpenAI(provider=provider)

        self._client: Any = client
        self._model_id = model_id
        self._max_output_tokens = max_output_tokens

    @staticmethod
    def _mantle_base_url(model_id: str, region_name: str) -> str:
        """Select the model family's documented Mantle API base path."""
        path = "openai/v1" if model_id.startswith("openai.gpt-5.") else "v1"
        return f"https://bedrock-mantle.{region_name}.api.aws/{path}"

    def generate(self, prompt: str) -> str:
        """Generate one stateless text response through Bedrock Mantle."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        try:
            generated = (
                self._generate_anthropic(prompt)
                if self._uses_anthropic_messages
                else (
                    self._generate_response(prompt)
                    if self._uses_openai_responses
                    else self._generate_chat_completion(prompt)
                )
            )
        except (AnthropicError, OpenAIError, BotoCoreError) as error:
            detail = str(error).strip()
            suffix = f": {detail[:500]}" if detail else ""
            raise LanguageModelError(
                f"Amazon Bedrock Mantle generation failed{suffix}"
            ) from error

        if not generated.strip():
            raise LanguageModelError("Amazon Bedrock Mantle returned no generated text")
        return generated.strip()

    def generate_with_tools(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
        *,
        max_rounds: int = 5,
    ) -> ToolCallingResult:
        """Let the model select client-side tools and consume their results."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not tools:
            raise ValueError("at least one tool is required")
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")

        try:
            if self._uses_anthropic_messages:
                return self._generate_anthropic_with_tools(
                    prompt, tools, execute_tool, max_rounds=max_rounds
                )
            if self._uses_openai_responses:
                return self._generate_response_with_tools(
                    prompt, tools, execute_tool, max_rounds=max_rounds
                )
            return self._generate_chat_completion_with_tools(
                prompt, tools, execute_tool, max_rounds=max_rounds
            )
        except (AnthropicError, OpenAIError, BotoCoreError) as error:
            detail = str(error).strip()
            suffix = f": {detail[:500]}" if detail else ""
            raise LanguageModelError(
                f"Amazon Bedrock Mantle tool calling failed{suffix}"
            ) from error

    def _generate_anthropic(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model_id,
            max_tokens=self._max_output_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if getattr(block, "type", None) == "text" and isinstance(text, str):
                text_parts.append(text)
        return "".join(text_parts)

    def _generate_response(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self._model_id,
            input=prompt,
            max_output_tokens=self._max_output_tokens,
            store=False,
        )
        generated = getattr(response, "output_text", None)
        return generated if isinstance(generated, str) else ""

    def _generate_response_with_tools(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
        *,
        max_rounds: int,
    ) -> ToolCallingResult:
        input_items: list[Any] = [{"role": "user", "content": prompt}]
        api_tools = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]
        records: list[ToolCallRecord] = []

        for round_index in range(max_rounds):
            response = self._client.responses.create(
                model=self._model_id,
                input=input_items,
                tools=api_tools,
                tool_choice="required" if round_index == 0 else "auto",
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
            output_items = list(getattr(response, "output", None) or [])
            input_items.extend(output_items)
            calls = [
                item
                for item in output_items
                if getattr(item, "type", None) == "function_call"
            ]
            if not calls:
                text = getattr(response, "output_text", None)
                return self._final_tool_result(text, records)

            for call in calls:
                name = getattr(call, "name", None)
                call_id = getattr(call, "call_id", None)
                raw_arguments = getattr(call, "arguments", None)
                record = self._execute_tool_call(
                    name,
                    raw_arguments,
                    tools,
                    execute_tool,
                )
                records.append(record)
                if not isinstance(call_id, str) or not call_id:
                    raise LanguageModelError("Model tool call did not include call_id")
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": record.output,
                    }
                )

        raise LanguageModelError("Model exceeded the tool-calling round limit")

    def _generate_chat_completion(self, prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self._max_output_tokens,
            temperature=0.1,
        )
        if not completion.choices:
            return ""
        content = completion.choices[0].message.content
        return content if isinstance(content, str) else ""

    def _generate_chat_completion_with_tools(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
        *,
        max_rounds: int,
    ) -> ToolCallingResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        api_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
        records: list[ToolCallRecord] = []

        for round_index in range(max_rounds):
            completion = self._client.chat.completions.create(
                model=self._model_id,
                messages=messages,
                tools=api_tools,
                tool_choice="required" if round_index == 0 else "auto",
                max_tokens=self._max_output_tokens,
                temperature=0.1,
            )
            if not completion.choices:
                raise LanguageModelError("Amazon Bedrock Mantle returned no choices")
            message = completion.choices[0].message
            calls = list(getattr(message, "tool_calls", None) or [])
            if not calls:
                return self._final_tool_result(
                    getattr(message, "content", None), records
                )

            serialized_calls: list[dict[str, object]] = []
            for call in calls:
                function = getattr(call, "function", None)
                name = getattr(function, "name", None)
                raw_arguments = getattr(function, "arguments", None)
                call_id = getattr(call, "id", None)
                if not isinstance(call_id, str) or not call_id:
                    raise LanguageModelError("Model tool call did not include an id")
                record = self._execute_tool_call(
                    name,
                    raw_arguments,
                    tools,
                    execute_tool,
                )
                records.append(record)
                serialized_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": record.name,
                            "arguments": (
                                raw_arguments
                                if isinstance(raw_arguments, str)
                                else json.dumps(record.arguments)
                            ),
                        },
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": record.output,
                    }
                )
            messages.insert(
                len(messages) - len(calls),
                {
                    "role": "assistant",
                    "content": getattr(message, "content", None) or "",
                    "tool_calls": serialized_calls,
                },
            )

        raise LanguageModelError("Model exceeded the tool-calling round limit")

    def _generate_anthropic_with_tools(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
        *,
        max_rounds: int,
    ) -> ToolCallingResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        api_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]
        records: list[ToolCallRecord] = []

        for round_index in range(max_rounds):
            response = self._client.messages.create(
                model=self._model_id,
                max_tokens=self._max_output_tokens,
                messages=messages,
                tools=api_tools,
                tool_choice={"type": "any" if round_index == 0 else "auto"},
            )
            content = list(getattr(response, "content", None) or [])
            calls = [
                block for block in content if getattr(block, "type", None) == "tool_use"
            ]
            if not calls:
                text = "".join(
                    block.text
                    for block in content
                    if getattr(block, "type", None) == "text"
                    and isinstance(getattr(block, "text", None), str)
                )
                return self._final_tool_result(text, records)

            messages.append({"role": "assistant", "content": content})
            tool_results: list[dict[str, object]] = []
            for call in calls:
                name = getattr(call, "name", None)
                raw_arguments = getattr(call, "input", None)
                call_id = getattr(call, "id", None)
                record = self._execute_tool_call(
                    name,
                    raw_arguments,
                    tools,
                    execute_tool,
                )
                records.append(record)
                if not isinstance(call_id, str) or not call_id:
                    raise LanguageModelError("Model tool call did not include an id")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "content": record.output,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        raise LanguageModelError("Model exceeded the tool-calling round limit")

    @staticmethod
    def _execute_tool_call(
        name: object,
        raw_arguments: object,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
    ) -> ToolCallRecord:
        resolved_name = name if isinstance(name, str) else ""
        known_names = {tool.name for tool in tools}
        try:
            if isinstance(raw_arguments, str):
                parsed = json.loads(raw_arguments)
            else:
                parsed = raw_arguments
            if not isinstance(parsed, dict) or not all(
                isinstance(key, str) for key in parsed
            ):
                raise ValueError("tool arguments must be a JSON object")
            arguments = dict(parsed)
            if resolved_name not in known_names:
                output = json.dumps({"error": f"Unknown tool: {resolved_name}"})
            else:
                output = execute_tool(resolved_name, arguments)
                if not isinstance(output, str):
                    raise TypeError("tool output must be text")
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            arguments = {}
            output = json.dumps({"error": str(error)})
        return ToolCallRecord(resolved_name, arguments, output)

    @staticmethod
    def _final_tool_result(
        text: object,
        records: list[ToolCallRecord],
    ) -> ToolCallingResult:
        if not isinstance(text, str) or not text.strip():
            raise LanguageModelError("Amazon Bedrock Mantle returned no generated text")
        return ToolCallingResult(text.strip(), tuple(records))
