"""Amazon Bedrock Runtime implementation of the language-model contract."""

from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)

from app.language_models.language_model import LanguageModelError


class BedrockLanguageModel:
    """Generate text through the normalized Amazon Bedrock Converse API."""

    def __init__(
        self,
        model_id: str,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        bedrock_runtime_client: Any | None = None,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("temperature must be between 0 and 1")

        if bedrock_runtime_client is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            bedrock_runtime_client = session.client("bedrock-runtime")

        self._client = bedrock_runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._temperature = temperature

    def generate(self, prompt: str) -> str:
        """Generate one text response from Bedrock."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": self._max_tokens,
                    "temperature": self._temperature,
                },
            )
            content_blocks = response["output"]["message"]["content"]
        except (BotoCoreError, ClientError) as error:
            raise LanguageModelError("Amazon Bedrock generation failed") from error
        except (KeyError, TypeError) as error:
            raise LanguageModelError(
                "Amazon Bedrock returned an invalid response structure"
            ) from error

        text_parts = [
            block["text"]
            for block in content_blocks
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ]
        generated = "".join(text_parts).strip()
        if not generated:
            raise LanguageModelError("Amazon Bedrock returned no generated text")
        return generated
