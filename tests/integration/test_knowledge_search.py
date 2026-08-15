"""Opt-in checks for Managed Knowledge Base configuration and retrieval."""

import os
from urllib.parse import urlparse

import boto3  # type: ignore[import-untyped]
import pytest

from app.config import ApplicationSettings
from app.tools import create_knowledge_retriever, search_process_knowledge

pytestmark = pytest.mark.integration


def test_managed_knowledge_base_configuration_and_retrieval() -> None:
    if os.getenv("RUN_KNOWLEDGE_BASE_INTEGRATION") != "1":
        pytest.skip("Set RUN_KNOWLEDGE_BASE_INTEGRATION=1 to allow paid retrieval")

    settings = ApplicationSettings.from_environment()
    if settings.bedrock_knowledge_base_id is None:
        pytest.skip("Set BEDROCK_KNOWLEDGE_BASE_ID from Terraform output")

    bucket_name = os.getenv("KNOWLEDGE_DOCUMENTS_BUCKET")
    documents_prefix = os.getenv("KNOWLEDGE_DOCUMENTS_PREFIX", "documents/")
    if not bucket_name:
        pytest.skip("Set KNOWLEDGE_DOCUMENTS_BUCKET from Terraform output")

    session = boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )
    control_client = session.client("bedrock-agent")
    response = control_client.get_knowledge_base(
        knowledgeBaseId=settings.bedrock_knowledge_base_id
    )
    configuration = response["knowledgeBase"]["knowledgeBaseConfiguration"]

    assert configuration["type"] == "MANAGED"
    managed = configuration["managedKnowledgeBaseConfiguration"]
    assert managed["embeddingModelType"] == "MANAGED"
    assert "embeddingModelArn" not in managed
    assert "vectorKnowledgeBaseConfiguration" not in configuration

    retriever = create_knowledge_retriever(settings)
    results = search_process_knowledge(
        retriever,
        "What should happen when required process evidence is missing?",
    )

    normalized_prefix = documents_prefix.strip("/")
    expected_source_prefix = f"s3://{bucket_name}/{normalized_prefix}/"
    assert results
    assert all(result.guidance for result in results)
    assert all(
        result.source_id.startswith(expected_source_prefix) for result in results
    )

    for result in results:
        location = urlparse(result.document_location)
        assert location.scheme == "https"
        assert location.hostname is not None
        assert location.hostname.startswith(f"{bucket_name}.s3")
        assert location.hostname.endswith(".amazonaws.com")
        assert location.path.startswith(f"/{normalized_prefix}/")
