"""Amazon Bedrock Mantle implementation of the language-model contract."""

from typing import Any

from anthropic import AnthropicBedrockMantle, AnthropicError
from botocore.exceptions import BotoCoreError  # type: ignore[import-untyped]
from openai import OpenAI, OpenAIError
from openai.providers import bedrock

from app.language_models.language_model import LanguageModelError


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
                base_url = f"https://bedrock-mantle.{region_name}.api.aws/v1"
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
