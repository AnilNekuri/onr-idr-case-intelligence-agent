"""Tests for environment-based repository selection."""

from pathlib import Path

import pytest

from app.config import (
    ApplicationSettings,
    CaseRepositoryKind,
    ConfigurationError,
)


def test_defaults_to_local_json_repository() -> None:
    settings = ApplicationSettings.from_environment({})

    assert settings.case_repository is CaseRepositoryKind.JSON
    assert settings.json_cases_path == Path("data/cases.json")
    assert settings.aws_region == "us-east-1"
    assert settings.aws_profile is None


def test_selects_dynamodb_repository_from_environment() -> None:
    settings = ApplicationSettings.from_environment(
        {
            "CASE_REPOSITORY": "dynamodb",
            "DYNAMODB_CASE_TABLE": "development-cases",
            "S3_CASE_DOCUMENTS_BUCKET": "development-documents",
            "AWS_REGION": "us-east-1",
            "AWS_PROFILE": "anekur-admin",
            "BEDROCK_MODEL_ID": "synthetic.model-v1",
            "BEDROCK_KNOWLEDGE_BASE_ID": "KB12345678",
            "AGENTCORE_RUNTIME_ARN": "arn:aws:bedrock-agentcore:runtime/example",
            "AGENTCORE_ENDPOINT_NAME": "live",
        }
    )

    assert settings.case_repository is CaseRepositoryKind.DYNAMODB
    assert settings.dynamodb_case_table == "development-cases"
    assert settings.s3_case_documents_bucket == "development-documents"
    assert settings.aws_profile == "anekur-admin"
    assert settings.bedrock_model_id == "synthetic.model-v1"
    assert settings.bedrock_knowledge_base_id == "KB12345678"
    assert settings.agentcore_runtime_arn == (
        "arn:aws:bedrock-agentcore:runtime/example"
    )
    assert settings.agentcore_endpoint_name == "live"


def test_dynamodb_selection_requires_table_name() -> None:
    with pytest.raises(ConfigurationError, match="DYNAMODB_CASE_TABLE"):
        ApplicationSettings.from_environment({"CASE_REPOSITORY": "dynamodb"})


def test_unknown_repository_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="CASE_REPOSITORY"):
        ApplicationSettings.from_environment({"CASE_REPOSITORY": "unknown"})


def test_invalid_knowledge_base_id_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="BEDROCK_KNOWLEDGE_BASE_ID"):
        ApplicationSettings.from_environment({"BEDROCK_KNOWLEDGE_BASE_ID": "not-an-id"})


def test_invalid_agentcore_endpoint_name_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="AGENTCORE_ENDPOINT_NAME"):
        ApplicationSettings.from_environment({"AGENTCORE_ENDPOINT_NAME": "not-live!"})
