"""Tests for the Streamlit-facing AgentCore runtime client."""

import json
from datetime import date
from io import BytesIO

import pytest

from app.agentcore_client import AgentCoreInvocationError, AgentCoreRuntimeClient


class _RecordingRuntimeClient:
    def __init__(self, response_body: bytes) -> None:
        self._response_body = response_body
        self.request: dict[str, object] | None = None

    def invoke_agent_runtime(self, **request: object) -> dict[str, object]:
        self.request = request
        return {"response": BytesIO(self._response_body)}


def test_invokes_configured_endpoint_and_parses_the_grounded_answer() -> None:
    runtime = _RecordingRuntimeClient(
        json.dumps(
            {
                "case_id": "CASE-1001",
                "generated_answer": "Request the missing response [guide].",
                "citations": [
                    {
                        "source_id": "guide",
                        "document_location": "s3://knowledge/guide.md",
                    }
                ],
                "unavailable_evidence": ["document:response.pdf"],
            }
        ).encode("utf-8")
    )
    client = AgentCoreRuntimeClient(
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/example",
        "live",
        runtime,
    )

    answer = client.answer(
        "CASE-1001",
        "What should happen next?",
        current_date=date(2026, 8, 14),
        runtime_session_id="12345678-1234-1234-1234-123456789012",
    )

    assert runtime.request is not None
    runtime_arn = runtime.request["agentRuntimeArn"]
    assert isinstance(runtime_arn, str)
    assert runtime_arn.endswith("runtime/example")
    assert runtime.request["qualifier"] == "live"
    assert runtime.request["runtimeSessionId"] == (
        "12345678-1234-1234-1234-123456789012"
    )
    assert json.loads(runtime.request["payload"]) == {  # type: ignore[arg-type]
        "case_id": "CASE-1001",
        "question": "What should happen next?",
        "current_date": "2026-08-14",
    }
    assert answer.generated_answer == "Request the missing response [guide]."
    assert answer.citations[0].model_dump() == {
        "source_id": "guide",
        "document_location": "s3://knowledge/guide.md",
    }
    assert answer.unavailable_evidence == ("document:response.pdf",)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({}, "response body"),
        ({"response": BytesIO(b"not-json")}, "valid JSON"),
        ({"response": BytesIO(b"[]")}, "JSON that was not an object"),
        (
            {
                "response": BytesIO(
                    json.dumps(
                        {
                            "case_id": "CASE-1001",
                            "generated_answer": "ok",
                            "citations": [{"source_id": "missing-location"}],
                        }
                    ).encode("utf-8")
                )
            },
            "invalid citations",
        ),
    ],
)
def test_rejects_invalid_runtime_responses(
    response: dict[str, object],
    message: str,
) -> None:
    class _SyntheticRuntimeClient:
        def invoke_agent_runtime(self, **request: object) -> dict[str, object]:
            return response

    client = AgentCoreRuntimeClient("runtime-arn", "live", _SyntheticRuntimeClient())

    with pytest.raises(AgentCoreInvocationError, match=message):
        client.answer(
            "CASE-1001",
            "What is the status?",
            current_date=date(2026, 8, 14),
            runtime_session_id="12345678-1234-1234-1234-123456789012",
        )
