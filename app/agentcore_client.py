"""Client boundary for invoking the deployed AgentCore case agent."""

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import boto3  # type: ignore[import-untyped]

from app.config import ApplicationSettings, ConfigurationError


class AgentCoreInvocationError(RuntimeError):
    """Raised when AgentCore returns an invalid invocation response."""


@dataclass(frozen=True, slots=True)
class AgentCoreCitation:
    """Citation returned by the deployed grounded agent."""

    source_id: str
    document_location: str

    def model_dump(self) -> dict[str, str]:
        """Return the citation in the UI's existing JSON-compatible shape."""
        return {
            "source_id": self.source_id,
            "document_location": self.document_location,
        }


@dataclass(frozen=True, slots=True)
class AgentCoreAnswer:
    """Subset of the deployed agent response consumed by Streamlit."""

    case_id: str
    generated_answer: str | None
    citations: tuple[AgentCoreCitation, ...]
    unavailable_evidence: tuple[str, ...]


class AgentCoreRuntimeClient:
    """Invoke one stable AgentCore runtime endpoint through the AWS SDK."""

    def __init__(
        self,
        runtime_arn: str,
        endpoint_name: str,
        runtime_client: Any,
    ) -> None:
        self._runtime_arn = runtime_arn
        self._endpoint_name = endpoint_name
        self._runtime_client = runtime_client

    def answer(
        self,
        case_id: str,
        question: str,
        *,
        current_date: date,
        runtime_session_id: str,
    ) -> AgentCoreAnswer:
        """Invoke the deployed agent and validate the fields used by the UI."""
        response = self._runtime_client.invoke_agent_runtime(
            agentRuntimeArn=self._runtime_arn,
            qualifier=self._endpoint_name,
            runtimeSessionId=runtime_session_id,
            payload=json.dumps(
                {
                    "case_id": case_id,
                    "question": question,
                    "current_date": current_date.isoformat(),
                }
            ).encode("utf-8"),
        )
        result = self._decode_response(response)
        return self._parse_answer(result)

    @staticmethod
    def _decode_response(response: Any) -> dict[str, object]:
        body = response.get("response")
        if body is None:
            raise AgentCoreInvocationError(
                "AgentCore response did not contain a response body"
            )

        try:
            if hasattr(body, "read"):
                raw = body.read()
            elif isinstance(body, (bytes, bytearray, str)):
                raw = body
            else:
                raw = b"".join(body)
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            result = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentCoreInvocationError(
                "AgentCore returned a response body that was not valid JSON"
            ) from error

        if not isinstance(result, dict):
            raise AgentCoreInvocationError(
                "AgentCore returned JSON that was not an object"
            )
        return result

    @staticmethod
    def _parse_answer(result: dict[str, object]) -> AgentCoreAnswer:
        case_id = result.get("case_id")
        generated_answer = result.get("generated_answer")
        citations = result.get("citations", [])
        unavailable = result.get("unavailable_evidence", [])

        if not isinstance(case_id, str) or not case_id:
            raise AgentCoreInvocationError(
                "AgentCore response did not contain a valid case_id"
            )
        if generated_answer is not None and not isinstance(generated_answer, str):
            raise AgentCoreInvocationError(
                "AgentCore response contained an invalid generated_answer"
            )
        if not isinstance(citations, list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("source_id"), str)
            and isinstance(item.get("document_location"), str)
            for item in citations
        ):
            raise AgentCoreInvocationError(
                "AgentCore response contained invalid citations"
            )
        if not isinstance(unavailable, list) or not all(
            isinstance(item, str) for item in unavailable
        ):
            raise AgentCoreInvocationError(
                "AgentCore response contained invalid unavailable evidence"
            )

        parsed_citations = tuple(
            AgentCoreCitation(
                source_id=item["source_id"],
                document_location=item["document_location"],
            )
            for item in citations
        )
        return AgentCoreAnswer(
            case_id=case_id,
            generated_answer=generated_answer,
            citations=parsed_citations,
            unavailable_evidence=tuple(unavailable),
        )


def create_agentcore_runtime_client(
    settings: ApplicationSettings,
) -> AgentCoreRuntimeClient:
    """Construct the SDK client for the configured live runtime endpoint."""
    if settings.agentcore_runtime_arn is None:
        raise ConfigurationError(
            "AGENTCORE_RUNTIME_ARN is required for the Case chat workflow"
        )
    if settings.agentcore_endpoint_name is None:
        raise ConfigurationError(
            "AGENTCORE_ENDPOINT_NAME is required for the Case chat workflow"
        )

    session = boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )
    return AgentCoreRuntimeClient(
        settings.agentcore_runtime_arn,
        settings.agentcore_endpoint_name,
        session.client("bedrock-agentcore"),
    )
