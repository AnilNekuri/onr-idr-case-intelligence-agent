"""Contract tests for the conversational AgentCore adapter."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.claim_intake_agentcore_adapter import invoke_claim_intake_agentcore
from app.config import ApplicationSettings, CaseRepositoryKind
from app.models import ClaimIntakeRequest

SESSION_ID = "12345678-1234-1234-1234-123456789012"


@dataclass
class Response:
    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {"state": "WELCOME", "message": "How can I help?"}


class Agent:
    def __init__(self) -> None:
        self.received: tuple[str, ClaimIntakeRequest] | None = None

    def handle(self, session_id: str, request: ClaimIntakeRequest) -> Response:
        self.received = (session_id, request)
        return Response()


def test_validates_and_delegates_one_runtime_event() -> None:
    agent = Agent()
    result = invoke_claim_intake_agentcore(
        {"action": "MESSAGE", "message": "I want to process a claim"},
        runtime_session_id=SESSION_ID,
        agent_factory=lambda _settings: agent,  # type: ignore[arg-type,return-value]
        settings_factory=_settings,
    )

    assert result == {"state": "WELCOME", "message": "How can I help?"}
    assert agent.received is not None
    assert agent.received[0] == SESSION_ID
    assert agent.received[1].message == "I want to process a claim"


def test_short_runtime_session_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 33"):
        invoke_claim_intake_agentcore(
            {"action": "START"},
            runtime_session_id="short",
            settings_factory=_settings,
        )


def _settings() -> ApplicationSettings:
    return ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile=None,
        dynamodb_case_table=None,
        s3_case_documents_bucket=None,
    )
