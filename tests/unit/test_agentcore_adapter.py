"""Tests for the thin AgentCore runtime boundary."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from app.agentcore_adapter import invoke_agentcore
from app.config import ApplicationSettings, CaseRepositoryKind


@dataclass
class _SyntheticAnswer:
    payload: dict[str, object]

    def model_dump(self) -> dict[str, object]:
        return self.payload


class _RecordingAgent:
    def __init__(self) -> None:
        self.received: tuple[str, str, date] | None = None

    def answer(
        self,
        case_id: str,
        question: str,
        *,
        current_date: date,
    ) -> _SyntheticAnswer:
        self.received = (case_id, question, current_date)
        return _SyntheticAnswer({"case_id": case_id, "generated_answer": "ok"})


def _settings() -> ApplicationSettings:
    return ApplicationSettings(
        case_repository=CaseRepositoryKind.JSON,
        json_cases_path=Path("data/cases.json"),
        aws_region="us-east-1",
        aws_profile=None,
        dynamodb_case_table=None,
        s3_case_documents_bucket=None,
        bedrock_model_id="synthetic.model-v1",
        bedrock_knowledge_base_id="ABCDEFGHIJ",
    )


def test_adapts_payload_without_changing_agent_business_contract() -> None:
    settings = _settings()
    agent = _RecordingAgent()

    result = invoke_agentcore(
        {
            "case_id": " CASE-1001 ",
            "question": " What should happen next? ",
            "current_date": "2026-08-14",
        },
        agent_factory=lambda received: agent if received is settings else None,  # type: ignore[arg-type,return-value]
        settings_factory=lambda: settings,
    )

    assert agent.received == (
        "CASE-1001",
        "What should happen next?",
        date(2026, 8, 14),
    )
    assert result == {"case_id": "CASE-1001", "generated_answer": "ok"}


def test_accepts_agentcore_prompt_alias() -> None:
    agent = _RecordingAgent()

    invoke_agentcore(
        {"case_id": "CASE-1001", "prompt": "Summarize the case."},
        agent_factory=lambda _settings: agent,  # type: ignore[arg-type,return-value]
        settings_factory=_settings,
    )

    assert agent.received is not None
    assert agent.received[:2] == ("CASE-1001", "Summarize the case.")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"question": "hello"}, "case_id"),
        ({"case_id": "CASE-1001"}, "question or prompt"),
        (
            {
                "case_id": "CASE-1001",
                "question": "hello",
                "current_date": "08/14/2026",
            },
            "YYYY-MM-DD",
        ),
    ],
)
def test_rejects_invalid_runtime_payloads(
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        invoke_agentcore(payload, settings_factory=_settings)
