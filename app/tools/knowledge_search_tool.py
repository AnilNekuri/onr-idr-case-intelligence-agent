"""Retrieval-only access to synthetic process guidance."""

from dataclasses import dataclass
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)

from app.config import ApplicationSettings, ConfigurationError


class KnowledgeSearchError(RuntimeError):
    """Raised when process-guidance retrieval fails or returns invalid data."""


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResult:
    """One process-guidance passage with inspectable retrieval provenance."""

    guidance: str
    source_id: str
    document_location: str
    score: float | None


class KnowledgeRetriever(Protocol):
    """Storage-independent process-guidance retrieval contract."""

    def retrieve(
        self,
        question: str,
        *,
        number_of_results: int = 5,
    ) -> tuple[KnowledgeSearchResult, ...]: ...


class BedrockKnowledgeRetriever:
    """Retrieve process guidance from one Bedrock Managed Knowledge Base."""

    _LOCATION_FIELDS = (
        ("s3Location", "uri"),
        ("customDocumentLocation", "id"),
        ("googleDriveLocation", "url"),
        ("kendraDocumentLocation", "uri"),
        ("oneDriveLocation", "url"),
        ("confluenceLocation", "url"),
        ("salesforceLocation", "url"),
        ("sharePointLocation", "url"),
        ("webLocation", "url"),
        ("sqlLocation", "query"),
    )

    def __init__(
        self,
        knowledge_base_id: str,
        *,
        region_name: str,
        profile_name: str | None = None,
        bedrock_agent_runtime_client: Any | None = None,
    ) -> None:
        if not knowledge_base_id.strip():
            raise ValueError("knowledge_base_id must not be empty")
        if not region_name.strip():
            raise ValueError("region_name must not be empty")

        if bedrock_agent_runtime_client is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            bedrock_agent_runtime_client = session.client("bedrock-agent-runtime")

        self._knowledge_base_id = knowledge_base_id
        self._client = bedrock_agent_runtime_client

    def retrieve(
        self,
        question: str,
        *,
        number_of_results: int = 5,
    ) -> tuple[KnowledgeSearchResult, ...]:
        """Call Retrieve with managed search and preserve returned provenance."""
        _validate_search_input(question, number_of_results)

        try:
            response = self._client.retrieve(
                knowledgeBaseId=self._knowledge_base_id,
                retrievalQuery={"type": "TEXT", "text": question.strip()},
                retrievalConfiguration={
                    "managedSearchConfiguration": {
                        "numberOfResults": number_of_results,
                    }
                },
            )
        except (BotoCoreError, ClientError) as error:
            raise KnowledgeSearchError(
                "Amazon Bedrock Knowledge Base retrieval failed"
            ) from error

        try:
            raw_results = response["retrievalResults"]
            if not isinstance(raw_results, list):
                raise TypeError("retrievalResults must be a list")
            return tuple(self._parse_result(item) for item in raw_results)
        except (KeyError, TypeError, ValueError) as error:
            raise KnowledgeSearchError(
                "Amazon Bedrock Knowledge Base returned an invalid response"
            ) from error

    @classmethod
    def _parse_result(cls, raw_result: object) -> KnowledgeSearchResult:
        if not isinstance(raw_result, dict):
            raise TypeError("retrieval result must be an object")

        raw_content = raw_result["content"]
        if not isinstance(raw_content, dict):
            raise TypeError("retrieval content must be an object")
        guidance = raw_content["text"]
        if not isinstance(guidance, str) or not guidance.strip():
            raise ValueError("retrieval guidance must be non-empty text")

        document_location = cls._extract_location(raw_result["location"])
        raw_source_id = raw_result.get("documentId")
        source_id = (
            raw_source_id.strip()
            if isinstance(raw_source_id, str) and raw_source_id.strip()
            else document_location
        )

        raw_score = raw_result.get("score")
        if raw_score is not None and (
            isinstance(raw_score, bool) or not isinstance(raw_score, (int, float))
        ):
            raise TypeError("retrieval score must be numeric")

        return KnowledgeSearchResult(
            guidance=guidance.strip(),
            source_id=source_id,
            document_location=document_location,
            score=float(raw_score) if raw_score is not None else None,
        )

    @classmethod
    def _extract_location(cls, raw_location: object) -> str:
        if not isinstance(raw_location, dict):
            raise TypeError("retrieval location must be an object")

        for container_key, value_key in cls._LOCATION_FIELDS:
            container = raw_location.get(container_key)
            if not isinstance(container, dict):
                continue
            value = container.get(value_key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise ValueError("retrieval result has no supported document location")


def search_process_knowledge(
    retriever: KnowledgeRetriever,
    question: str,
    *,
    number_of_results: int = 5,
) -> tuple[KnowledgeSearchResult, ...]:
    """Retrieve process guidance without generating an answer or case facts."""
    _validate_search_input(question, number_of_results)
    return retriever.retrieve(question, number_of_results=number_of_results)


def create_knowledge_retriever(
    settings: ApplicationSettings,
) -> BedrockKnowledgeRetriever:
    """Construct the configured Bedrock retrieval-only adapter."""
    if settings.bedrock_knowledge_base_id is None:
        raise ConfigurationError(
            "BEDROCK_KNOWLEDGE_BASE_ID is required for knowledge retrieval"
        )
    return BedrockKnowledgeRetriever(
        settings.bedrock_knowledge_base_id,
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )


def _validate_search_input(question: str, number_of_results: int) -> None:
    if not question.strip():
        raise ValueError("question must not be empty")
    if not 1 <= number_of_results <= 100:
        raise ValueError("number_of_results must be between 1 and 100")
