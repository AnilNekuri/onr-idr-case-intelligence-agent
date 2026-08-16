"""Tests for selecting Mantle or Runtime extraction at composition time."""

from pathlib import Path
from typing import Any

import pytest

import app.services.factory as service_factory
from app.config import (
    ApplicationSettings,
    BedrockExtractionApi,
    CaseRepositoryKind,
    ConfigurationError,
)
from app.services import MantleExtractionService


def settings(
    *,
    api: BedrockExtractionApi = BedrockExtractionApi.MANTLE,
    extraction_model_id: str | None = "anthropic.claude-haiku-4-5",
) -> ApplicationSettings:
    return ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile="synthetic-profile",
        dynamodb_case_table=None,
        s3_case_documents_bucket="synthetic-documents",
        bedrock_model_id="anthropic.claude-haiku-4-5",
        bedrock_extraction_model_id=extraction_model_id,
        bedrock_extraction_api=api,
    )


def test_mantle_is_default_extraction_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, Any] = {}

    class FakeMantleModel:
        def __init__(self, model_id: str, **kwargs: Any) -> None:
            created["model_id"] = model_id
            created.update(kwargs)

        def generate(self, prompt: str) -> str:
            return prompt

    monkeypatch.setattr(
        service_factory, "BedrockMantleLanguageModel", FakeMantleModel
    )
    monkeypatch.setattr(
        service_factory, "create_document_repository", lambda _: object()
    )
    monkeypatch.setattr(
        service_factory, "TextractService", lambda *args, **kwargs: object()
    )

    service = service_factory.create_document_extraction_service(settings())

    assert isinstance(service._bedrock_service, MantleExtractionService)
    assert created == {
        "model_id": "anthropic.claude-haiku-4-5",
        "region_name": "us-east-1",
        "profile_name": "synthetic-profile",
        "max_output_tokens": 2048,
    }


def test_runtime_remains_available_when_explicitly_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRuntimeExtractor:
        def __init__(self, model_id: str, **kwargs: Any) -> None:
            self.model_id = model_id

    monkeypatch.setattr(
        service_factory, "create_document_repository", lambda _: object()
    )
    monkeypatch.setattr(
        service_factory, "TextractService", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        service_factory, "BedrockExtractionService", FakeRuntimeExtractor
    )

    service = service_factory.create_document_extraction_service(
        settings(
            api=BedrockExtractionApi.RUNTIME,
            extraction_model_id="anthropic.claude-haiku-runtime-v1:0",
        )
    )

    assert isinstance(service._bedrock_service, FakeRuntimeExtractor)
    assert service._bedrock_service.model_id == (
        "anthropic.claude-haiku-runtime-v1:0"
    )


def test_runtime_requires_an_explicit_runtime_model_id() -> None:
    with pytest.raises(ConfigurationError, match="BEDROCK_EXTRACTION_MODEL_ID"):
        service_factory.create_document_extraction_service(
            settings(
                api=BedrockExtractionApi.RUNTIME,
                extraction_model_id=None,
            )
        )
