"""Local tests for retrieval-only process knowledge search."""

from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.config import ApplicationSettings, CaseRepositoryKind, ConfigurationError
from app.tools import (
    BedrockKnowledgeRetriever,
    KnowledgeSearchError,
    KnowledgeSearchResult,
    create_knowledge_retriever,
    search_process_knowledge,
)


class FakeBedrockAgentRuntimeClient:
    def __init__(self, response: object) -> None:
        self.response = response
        self.request: dict[str, Any] | None = None
        self.error: ClientError | None = None

    def retrieve(self, **kwargs: Any) -> object:
        self.request = kwargs
        if self.error is not None:
            raise self.error
        return self.response


def test_search_uses_retrieve_with_managed_search_and_preserves_sources() -> None:
    client = FakeBedrockAgentRuntimeClient(
        {
            "retrievalResults": [
                {
                    "content": {
                        "type": "TEXT",
                        "text": "Record missing evidence before escalation.",
                    },
                    "documentId": "DOC-SYNTHETIC-1",
                    "location": {
                        "type": "S3",
                        "s3Location": {
                            "uri": "s3://knowledge/documents/onr_process.md"
                        },
                    },
                    "score": 0.91,
                },
                {
                    "content": {"text": "Do not infer an unavailable response."},
                    "location": {
                        "type": "S3",
                        "s3Location": {
                            "uri": "s3://knowledge/documents/citation_rules.md"
                        },
                    },
                },
            ]
        }
    )
    retriever = BedrockKnowledgeRetriever(
        "KB12345678",
        region_name="us-east-1",
        bedrock_agent_runtime_client=client,
    )

    results = search_process_knowledge(
        retriever,
        "What should happen when evidence is missing?",
        number_of_results=2,
    )

    assert client.request == {
        "knowledgeBaseId": "KB12345678",
        "retrievalQuery": {
            "type": "TEXT",
            "text": "What should happen when evidence is missing?",
        },
        "retrievalConfiguration": {
            "managedSearchConfiguration": {"numberOfResults": 2}
        },
    }
    assert results == (
        KnowledgeSearchResult(
            guidance="Record missing evidence before escalation.",
            source_id="DOC-SYNTHETIC-1",
            document_location="s3://knowledge/documents/onr_process.md",
            score=0.91,
        ),
        KnowledgeSearchResult(
            guidance="Do not infer an unavailable response.",
            source_id="s3://knowledge/documents/citation_rules.md",
            document_location="s3://knowledge/documents/citation_rules.md",
            score=None,
        ),
    )


def test_empty_results_are_returned_without_generation() -> None:
    client = FakeBedrockAgentRuntimeClient({"retrievalResults": []})
    retriever = BedrockKnowledgeRetriever(
        "KB12345678",
        region_name="us-east-1",
        bedrock_agent_runtime_client=client,
    )

    assert search_process_knowledge(retriever, "Unknown process topic") == ()
    assert client.request is not None


@pytest.mark.parametrize(
    ("question", "number_of_results", "message"),
    [
        (" ", 5, "question"),
        ("guidance", 0, "number_of_results"),
        ("guidance", 101, "number_of_results"),
    ],
)
def test_invalid_search_input_is_rejected_before_the_aws_call(
    question: str,
    number_of_results: int,
    message: str,
) -> None:
    client = FakeBedrockAgentRuntimeClient({"retrievalResults": []})
    retriever = BedrockKnowledgeRetriever(
        "KB12345678",
        region_name="us-east-1",
        bedrock_agent_runtime_client=client,
    )

    with pytest.raises(ValueError, match=message):
        search_process_knowledge(
            retriever,
            question,
            number_of_results=number_of_results,
        )

    assert client.request is None


def test_aws_failure_is_wrapped() -> None:
    client = FakeBedrockAgentRuntimeClient({"retrievalResults": []})
    client.error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
        "Retrieve",
    )
    retriever = BedrockKnowledgeRetriever(
        "KB12345678",
        region_name="us-east-1",
        bedrock_agent_runtime_client=client,
    )

    with pytest.raises(KnowledgeSearchError, match="retrieval failed"):
        search_process_knowledge(retriever, "Find process guidance")


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"retrievalResults": "not-a-list"},
        {"retrievalResults": [{"content": {"text": ""}, "location": {}}]},
        {"retrievalResults": [{"content": {"text": "guidance"}, "location": {}}]},
    ],
)
def test_invalid_aws_response_is_rejected(response: object) -> None:
    retriever = BedrockKnowledgeRetriever(
        "KB12345678",
        region_name="us-east-1",
        bedrock_agent_runtime_client=FakeBedrockAgentRuntimeClient(response),
    )

    with pytest.raises(KnowledgeSearchError, match="invalid response"):
        search_process_knowledge(retriever, "Find process guidance")


def test_factory_requires_knowledge_base_id() -> None:
    settings = ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile=None,
        dynamodb_case_table=None,
        s3_case_documents_bucket=None,
    )

    with pytest.raises(ConfigurationError, match="BEDROCK_KNOWLEDGE_BASE_ID"):
        create_knowledge_retriever(settings)
