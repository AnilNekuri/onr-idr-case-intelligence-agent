"""Tests for repository construction outside the service layer."""

from pathlib import Path
from typing import Any

import pytest

import app.repositories.factory as repository_factory
from app.config import (
    ApplicationSettings,
    CaseRepositoryKind,
    ConfigurationError,
)
from app.repositories import JsonCaseRepository


def settings(
    *,
    repository: CaseRepositoryKind = CaseRepositoryKind.JSON,
    table_name: str | None = None,
    bucket_name: str | None = None,
) -> ApplicationSettings:
    return ApplicationSettings(
        case_repository=repository,
        json_cases_path=Path("synthetic-cases.json"),
        aws_region="us-east-1",
        aws_profile="anekur-admin",
        dynamodb_case_table=table_name,
        s3_case_documents_bucket=bucket_name,
    )


def test_creates_json_repository() -> None:
    repository = repository_factory.create_case_repository(settings())

    assert isinstance(repository, JsonCaseRepository)


def test_creates_dynamodb_repository_with_aws_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    class FakeDynamoRepository:
        def __init__(self, table_name: str, **kwargs: Any) -> None:
            received["table_name"] = table_name
            received.update(kwargs)

        def get(self, case_id: str) -> None:
            return None

        def save(self, case: Any) -> None:
            return None

    monkeypatch.setattr(
        repository_factory,
        "DynamoDbCaseRepository",
        FakeDynamoRepository,
    )

    repository_factory.create_case_repository(
        settings(
            repository=CaseRepositoryKind.DYNAMODB,
            table_name="development-cases",
        )
    )

    assert received == {
        "table_name": "development-cases",
        "region_name": "us-east-1",
        "profile_name": "anekur-admin",
    }


def test_document_repository_requires_bucket() -> None:
    with pytest.raises(ConfigurationError, match="S3_CASE_DOCUMENTS_BUCKET"):
        repository_factory.create_document_repository(settings())


def test_creates_s3_repository_with_aws_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    class FakeS3Repository:
        def __init__(self, bucket_name: str, **kwargs: Any) -> None:
            received["bucket_name"] = bucket_name
            received.update(kwargs)

    monkeypatch.setattr(
        repository_factory,
        "S3DocumentRepository",
        FakeS3Repository,
    )

    repository_factory.create_document_repository(
        settings(bucket_name="development-documents")
    )

    assert received == {
        "bucket_name": "development-documents",
        "region_name": "us-east-1",
        "profile_name": "anekur-admin",
    }
