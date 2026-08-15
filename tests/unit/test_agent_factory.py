"""Tests for assembling all configured Step 13 agent dependencies."""

from pathlib import Path

import pytest

import app.services.factory as agent_factory
from app.config import ApplicationSettings, CaseRepositoryKind
from app.services import GroundedCaseAgent


def test_assembles_repository_mantle_model_and_knowledge_retriever(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile="synthetic-profile",
        dynamodb_case_table=None,
        s3_case_documents_bucket=None,
        bedrock_model_id="synthetic.model-v1",
        bedrock_knowledge_base_id="ABCDEFGHIJ",
    )
    repository = object()
    language_model = object()
    knowledge_retriever = object()

    monkeypatch.setattr(
        agent_factory,
        "create_case_repository",
        lambda received: repository if received is settings else None,
    )
    monkeypatch.setattr(
        agent_factory,
        "create_language_model",
        lambda received: language_model if received is settings else None,
    )
    monkeypatch.setattr(
        agent_factory,
        "create_knowledge_retriever",
        lambda received: knowledge_retriever if received is settings else None,
    )

    agent = agent_factory.create_grounded_case_agent(settings)

    assert isinstance(agent, GroundedCaseAgent)
    assert agent._repository is repository
    assert agent._language_model is language_model
    assert agent._knowledge_retriever is knowledge_retriever
