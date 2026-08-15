"""Local tests for the Bedrock Mantle language-model adapter."""

from types import SimpleNamespace
from typing import Any

import pytest
from anthropic import AnthropicError
from openai import OpenAIError

from app.language_models import BedrockMantleLanguageModel, LanguageModelError


class FakeResponses:
    """Record Responses API requests and return a configurable result."""

    def __init__(self, output_text: object = "Synthetic Mantle summary.") -> None:
        self.output_text = output_text
        self.request: dict[str, Any] | None = None
        self.error: OpenAIError | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses | None = None) -> None:
        self.responses = responses or FakeResponses()


class FakeMessages:
    """Record Anthropic Messages requests and return text content blocks."""

    def __init__(self) -> None:
        self.request: dict[str, Any] | None = None
        self.error: AnthropicError | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Claude summary. "),
                SimpleNamespace(type="tool_use", name="ignored"),
                SimpleNamespace(type="text", text="Second fact."),
            ]
        )


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def test_generate_uses_stateless_responses_api() -> None:
    client = FakeOpenAIClient()
    model = BedrockMantleLanguageModel(
        "openai.synthetic-mantle-model-v1",
        region_name="us-east-1",
        max_output_tokens=256,
        client=client,
    )

    result = model.generate("Summarize supplied facts.")

    assert result == "Synthetic Mantle summary."
    assert client.responses.request == {
        "model": "openai.synthetic-mantle-model-v1",
        "input": "Summarize supplied facts.",
        "max_output_tokens": 256,
        "store": False,
    }


class FakeChatCompletions:
    def __init__(self, content: object = "Mistral summary.") -> None:
        self.content = content
        self.request: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeChat:
    def __init__(self, completions: FakeChatCompletions | None = None) -> None:
        self.completions = completions or FakeChatCompletions()


class FakeChatClient:
    def __init__(self, completions: FakeChatCompletions | None = None) -> None:
        self.chat = FakeChat(completions)


def test_mistral_model_uses_chat_completions_api() -> None:
    client = FakeChatClient()
    model = BedrockMantleLanguageModel(
        "mistral.ministral-3-3b-instruct",
        region_name="us-east-1",
        max_output_tokens=256,
        client=client,
    )

    result = model.generate("Summarize supplied facts.")

    assert result == "Mistral summary."
    assert client.chat.completions.request == {
        "model": "mistral.ministral-3-3b-instruct",
        "messages": [{"role": "user", "content": "Summarize supplied facts."}],
        "max_tokens": 256,
        "temperature": 0.1,
    }


def test_anthropic_model_uses_messages_api() -> None:
    client = FakeAnthropicClient()
    model = BedrockMantleLanguageModel(
        "anthropic.claude-haiku-4-5",
        region_name="us-east-1",
        max_output_tokens=256,
        client=client,
    )

    result = model.generate("Summarize supplied facts.")

    assert result == "Claude summary. Second fact."
    assert client.messages.request == {
        "model": "anthropic.claude-haiku-4-5",
        "max_tokens": 256,
        "messages": [{"role": "user", "content": "Summarize supplied facts."}],
    }


def test_anthropic_failure_includes_safe_sdk_detail() -> None:
    client = FakeAnthropicClient()
    client.messages.error = AnthropicError("synthetic Anthropic failure")
    model = BedrockMantleLanguageModel(
        "anthropic.claude-haiku-4-5",
        region_name="us-east-1",
        client=client,
    )

    with pytest.raises(
        LanguageModelError,
        match="Mantle generation failed: synthetic Anthropic failure",
    ):
        model.generate("Facts")


def test_failed_mantle_request_is_wrapped() -> None:
    client = FakeOpenAIClient()
    client.responses.error = OpenAIError("synthetic failure")
    model = BedrockMantleLanguageModel(
        "openai.synthetic-mantle-model-v1",
        region_name="us-east-1",
        client=client,
    )

    with pytest.raises(LanguageModelError, match="Mantle generation failed"):
        model.generate("Facts")


@pytest.mark.parametrize("output_text", [None, "", "   ", 123])
def test_empty_or_invalid_output_is_rejected(output_text: object) -> None:
    model = BedrockMantleLanguageModel(
        "openai.synthetic-mantle-model-v1",
        region_name="us-east-1",
        client=FakeOpenAIClient(FakeResponses(output_text)),
    )

    with pytest.raises(LanguageModelError, match="no generated text"):
        model.generate("Facts")


def test_empty_prompt_is_rejected_before_mantle_call() -> None:
    client = FakeOpenAIClient()
    model = BedrockMantleLanguageModel(
        "openai.synthetic-mantle-model-v1",
        region_name="us-east-1",
        client=client,
    )

    with pytest.raises(ValueError, match="prompt must not be empty"):
        model.generate(" ")

    assert client.responses.request is None


@pytest.mark.parametrize(
    ("model_id", "region_name", "max_output_tokens", "message"),
    [
        (" ", "us-east-1", 512, "model_id"),
        ("model", " ", 512, "region_name"),
        ("model", "us-east-1", 0, "max_output_tokens"),
    ],
)
def test_invalid_configuration_is_rejected(
    model_id: str,
    region_name: str,
    max_output_tokens: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BedrockMantleLanguageModel(
            model_id,
            region_name=region_name,
            max_output_tokens=max_output_tokens,
            client=FakeOpenAIClient(),
        )
