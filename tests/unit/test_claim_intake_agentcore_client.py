"""Tests for the Streamlit-facing claim-intake runtime client."""

import json
from io import BytesIO

from app.claim_intake_agentcore_client import ClaimIntakeAgentCoreClient
from app.models import ClaimIntakeAction, ClaimIntakeRequest

SESSION_ID = "12345678-1234-1234-1234-123456789012"


class RuntimeClient:
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def invoke_agent_runtime(self, **request: object) -> dict[str, object]:
        self.request = request
        return {
            "response": BytesIO(
                json.dumps(
                    {
                        "session_id": SESSION_ID,
                        "state": "WELCOME",
                        "message": "How can I help?",
                        "expected_input": "MESSAGE",
                    }
                ).encode()
            )
        }


def test_invokes_dedicated_runtime_with_structured_event() -> None:
    runtime = RuntimeClient()
    client = ClaimIntakeAgentCoreClient("runtime-arn", "live", runtime)

    response = client.invoke(
        ClaimIntakeRequest(action=ClaimIntakeAction.START),
        runtime_session_id=SESSION_ID,
    )

    assert response.message == "How can I help?"
    assert runtime.request is not None
    assert runtime.request["runtimeSessionId"] == SESSION_ID
    assert json.loads(runtime.request["payload"]) == {"action": "START"}  # type: ignore[arg-type]
