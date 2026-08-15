"""Tests for language-model construction at the composition boundary."""

from pathlib import Path
from typing import Any

import pytest

import app.language_models.factory as model_factory
from app.config import ApplicationSettings, CaseRepositoryKind, ConfigurationError


def settings(model_id: str | None) -> ApplicationSettings:
    return ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile="anekur-admin",
        dynamodb_case_table=None,
        s3_case_documents_bucket=None,
        bedrock_model_id=model_id,
    )


def test_model_id_is_required() -> None:
    with pytest.raises(ConfigurationError, match="BEDROCK_MODEL_ID"):
        model_factory.create_language_model(settings(None))


def test_creates_bedrock_model_with_aws_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    class FakeBedrockMantleModel:
        def __init__(self, model_id: str, **kwargs: Any) -> None:
            received["model_id"] = model_id
            received.update(kwargs)

        def generate(self, prompt: str) -> str:
            return prompt

    monkeypatch.setattr(
        model_factory,
        "BedrockMantleLanguageModel",
        FakeBedrockMantleModel,
    )

    model_factory.create_language_model(settings("synthetic.model-v1"))

    assert received == {
        "model_id": "synthetic.model-v1",
        "region_name": "us-east-1",
        "profile_name": "anekur-admin",
    }
