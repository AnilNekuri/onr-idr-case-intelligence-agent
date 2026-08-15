"""Local tests for the Bedrock language-model adapter."""

from typing import Any

import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.language_models import BedrockLanguageModel, LanguageModelError


class FakeBedrockRuntimeClient:
    """Record Converse requests and return a configurable response."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = (
            response
            if response is not None
            else {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [{"text": "Synthetic summary."}],
                    }
                }
            }
        )
        self.request: dict[str, Any] | None = None
        self.error: ClientError | None = None

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.request = kwargs
        if self.error is not None:
            raise self.error
        return self.response


def test_generate_uses_normalized_converse_api() -> None:
    client = FakeBedrockRuntimeClient()
    model = BedrockLanguageModel(
        "synthetic.model-v1",
        max_tokens=256,
        temperature=0.0,
        bedrock_runtime_client=client,
    )

    result = model.generate("Summarize supplied facts.")

    assert result == "Synthetic summary."
    assert client.request == {
        "modelId": "synthetic.model-v1",
        "messages": [
            {
                "role": "user",
                "content": [{"text": "Summarize supplied facts."}],
            }
        ],
        "inferenceConfig": {"maxTokens": 256, "temperature": 0.0},
    }


def test_generate_combines_text_content_blocks() -> None:
    client = FakeBedrockRuntimeClient(
        {
            "output": {
                "message": {
                    "content": [
                        {"text": "First sentence. "},
                        {"other": "ignored"},
                        {"text": "Second sentence."},
                    ]
                }
            }
        }
    )
    model = BedrockLanguageModel(
        "synthetic.model-v1",
        bedrock_runtime_client=client,
    )

    assert model.generate("Facts") == "First sentence. Second sentence."


def test_aws_failure_is_wrapped() -> None:
    client = FakeBedrockRuntimeClient()
    client.error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
        "Converse",
    )
    model = BedrockLanguageModel(
        "synthetic.model-v1",
        bedrock_runtime_client=client,
    )

    with pytest.raises(LanguageModelError, match="generation failed"):
        model.generate("Facts")


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"output": {"message": {"content": []}}},
        {"output": {"message": {"content": [{"not-text": "value"}]}}},
    ],
)
def test_invalid_or_empty_response_is_rejected(response: dict[str, Any]) -> None:
    model = BedrockLanguageModel(
        "synthetic.model-v1",
        bedrock_runtime_client=FakeBedrockRuntimeClient(response),
    )

    with pytest.raises(LanguageModelError):
        model.generate("Facts")


def test_empty_prompt_is_rejected_before_aws_call() -> None:
    client = FakeBedrockRuntimeClient()
    model = BedrockLanguageModel(
        "synthetic.model-v1",
        bedrock_runtime_client=client,
    )

    with pytest.raises(ValueError, match="prompt must not be empty"):
        model.generate(" ")

    assert client.request is None
