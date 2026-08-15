"""Step 13 tests for the assembled grounded case agent."""

import json
from datetime import date
from typing import Any, cast

import pytest

from app.models import Case, CaseEvent, CaseEventType, CaseStatus
from app.services import GroundedCaseAgent, UngroundedRecommendationError
from app.tools import KnowledgeSearchError, KnowledgeSearchResult
from tests.unit.tool_support import make_case

CURRENT_DATE = date(2026, 8, 10)


class RecordingRepository:
    def __init__(self, case: Case, events: list[str]) -> None:
        self._case = case
        self._events = events

    def get(self, case_id: str) -> Case | None:
        self._events.append("get_case")
        return self._case if case_id == self._case.case_id else None

    def save(self, case: Case) -> None:
        self._case = case


class RecordingRetriever:
    def __init__(
        self,
        events: list[str],
        results: tuple[KnowledgeSearchResult, ...],
    ) -> None:
        self._events = events
        self._results = results
        self.questions: list[str] = []

    def retrieve(
        self,
        question: str,
        *,
        number_of_results: int = 5,
    ) -> tuple[KnowledgeSearchResult, ...]:
        self._events.append("search_process_knowledge")
        self.questions.append(question)
        assert number_of_results == 5
        return self._results


class FailingRetriever:
    def retrieve(
        self,
        question: str,
        *,
        number_of_results: int = 5,
    ) -> tuple[KnowledgeSearchResult, ...]:
        raise KnowledgeSearchError("synthetic retrieval failure")


class RecordingModel:
    def __init__(self, events: list[str]) -> None:
        self._events = events
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self._events.append("model.generate")
        self.prompts.append(prompt)
        return "Use the grounded process guidance [blocker-guide]."


def make_blocked_case() -> Case:
    return make_case(
        status=CaseStatus.PENDING_PROVIDER_RESPONSE,
        missing_documents=["provider-response.pdf"],
        events=[
            CaseEvent(
                date=date(2026, 8, 5),
                type=CaseEventType.NOTICE_SENT,
                description="Notice sent",
            ),
            CaseEvent(
                date=date(2026, 8, 1),
                type=CaseEventType.CASE_CREATED,
                description="Case created",
            ),
        ],
    )


def guidance_results() -> tuple[KnowledgeSearchResult, ...]:
    return (
        KnowledgeSearchResult(
            guidance="Request the missing response before proceeding.",
            source_id="blocker-guide",
            document_location="s3://knowledge/required-information.md",
            score=0.97,
        ),
    )


def extract_json_block(prompt: str, tag: str) -> object:
    start_tag = f"<{tag}>\n"
    end_tag = f"\n</{tag}>"
    start = prompt.index(start_tag) + len(start_tag)
    end = prompt.index(end_tag)
    return json.loads(prompt[start:end])


@pytest.mark.parametrize(
    ("question", "needs_guidance"),
    [
        ("What is the case status?", False),
        ("What information is missing?", False),
        ("Is the deadline at risk?", False),
        ("Why is the case blocked?", True),
        ("What should happen next?", True),
    ],
)
def test_five_required_questions_use_expected_retrievals_before_generation(
    question: str,
    needs_guidance: bool,
) -> None:
    events: list[str] = []
    retriever = RecordingRetriever(events, guidance_results())
    model = RecordingModel(events)
    answer = GroundedCaseAgent(
        RecordingRepository(make_blocked_case(), events),
        model,
        retriever,
    ).answer("CASE-1001", question, current_date=CURRENT_DATE)

    expected_events = ["get_case"]
    if needs_guidance:
        expected_events.append("search_process_knowledge")
    expected_events.append("model.generate")
    assert events == expected_events
    assert answer.process_guidance_required is needs_guidance
    assert bool(answer.process_guidance) is needs_guidance
    assert bool(answer.citations) is needs_guidance
    assert retriever.questions == ([question] if needs_guidance else [])


def test_answer_records_every_tool_result_and_preserves_citations() -> None:
    events: list[str] = []
    model = RecordingModel(events)
    answer = GroundedCaseAgent(
        RecordingRepository(make_blocked_case(), events),
        model,
        RecordingRetriever(events, guidance_results()),
    ).answer(
        "CASE-1001",
        "What should happen next?",
        current_date=CURRENT_DATE,
    )

    dumped = answer.model_dump()
    tool_results = dumped["tool_results"]
    assert isinstance(tool_results, dict)
    assert tool_results["get_case"]["status"] == "PENDING_PROVIDER_RESPONSE"
    assert [event["date"] for event in tool_results["get_case_timeline"]] == [
        "2026-08-01",
        "2026-08-05",
    ]
    assert tool_results["get_missing_information"] == [
        "document:provider-response.pdf",
        "response:provider_response",
    ]
    assert tool_results["calculate_deadline_risk"] == {
        "deadline": "2026-08-31",
        "days_remaining": 21,
        "risk": "LOW",
    }
    assert tool_results["search_process_knowledge"] == [
        {
            "guidance": "Request the missing response before proceeding.",
            "source_id": "blocker-guide",
            "document_location": "s3://knowledge/required-information.md",
            "score": 0.97,
        }
    ]
    assert dumped["citations"] == [
        {
            "source_id": "blocker-guide",
            "document_location": "s3://knowledge/required-information.md",
        }
    ]
    assert dumped["generated_answer"] == answer.generated_answer

    authoritative = cast(
        dict[str, Any],
        extract_json_block(
            model.prompts[0],
            "AUTHORITATIVE_EVIDENCE_JSON",
        ),
    )
    guidance = cast(
        list[dict[str, Any]],
        extract_json_block(model.prompts[0], "PROCESS_GUIDANCE_JSON"),
    )
    assert authoritative["case"]["case_id"] == "CASE-1001"
    assert authoritative["deadline"]["risk"] == "LOW"
    assert guidance[0]["source_id"] == "blocker-guide"
    assert guidance[0]["document_location"].endswith("required-information.md")


@pytest.mark.parametrize("retriever", [None, FailingRetriever()])
def test_unavailable_process_guidance_is_reported_honestly(
    retriever: FailingRetriever | None,
) -> None:
    events: list[str] = []
    answer = GroundedCaseAgent(
        RecordingRepository(make_blocked_case(), events),
        RecordingModel(events),
        retriever,
    ).answer(
        "CASE-1001",
        "Why is the case blocked?",
        current_date=CURRENT_DATE,
    )

    assert "process_guidance" in answer.unavailable_evidence
    assert answer.process_guidance == ()
    assert answer.citations == ()
    assert events[-1] == "model.generate"


def test_guidance_source_tokens_are_valid_grounded_output() -> None:
    case = make_blocked_case()
    GroundedCaseAgent.validate_recommendation(
        case,
        "Consult required-information.md.",
        process_guidance=guidance_results(),
    )


def test_numbered_guidance_source_allows_ordering_prefix_alias() -> None:
    guidance = (
        KnowledgeSearchResult(
            guidance="Continue the documented open-negotiation workflow.",
            source_id="s3://knowledge/02_open_negotiation_workflow.md",
            document_location="s3://knowledge/02_open_negotiation_workflow.md",
            score=0.97,
        ),
    )

    GroundedCaseAgent.validate_recommendation(
        make_blocked_case(),
        "Follow open_negotiation_workflow.md.",
        process_guidance=guidance,
    )


def test_guidance_alias_does_not_allow_an_unrelated_document() -> None:
    with pytest.raises(UngroundedRecommendationError, match="unrelated.md"):
        GroundedCaseAgent.validate_recommendation(
            make_blocked_case(),
            "Follow unrelated.md.",
            process_guidance=guidance_results(),
        )
