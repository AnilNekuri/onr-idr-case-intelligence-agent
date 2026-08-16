"""State-machine tests for conversational claim intake."""

import json
from datetime import UTC, date, datetime

from app.language_models import ToolCallingResult, ToolCallRecord
from app.models import (
    CaseType,
    ClaimIntakeAction,
    ClaimIntakeRecord,
    ClaimIntakeRequest,
    ClaimIntakeStage,
    DisputeDocumentExtraction,
    DisputeDocumentType,
    ExtractedDisputeDocument,
    ExtractionSource,
    StoredIntakeDocument,
)
from app.services import CaseService, ConversationalClaimAgent
from app.services.knowledge_chat_service import (
    GeneralKnowledgeAnswer,
    KnowledgeCitation,
)
from app.tools import KnowledgeSearchResult
from tests.unit.tool_support import StubCaseRepository

SESSION_ID = "12345678-1234-1234-1234-123456789012"
DOCUMENT = StoredIntakeDocument(
    document_id="DOC-1",
    file_name="notice.pdf",
    s3_key=f"temporary/INTAKE-{SESSION_ID}/DOC-1/notice.pdf",
)


class StateRepository:
    def __init__(self) -> None:
        self.records: dict[str, ClaimIntakeRecord] = {}

    def get(self, session_id: str) -> ClaimIntakeRecord | None:
        return self.records.get(session_id)

    def save(self, record: ClaimIntakeRecord) -> None:
        self.records[record.session_id] = record


class RoutingModel:
    def __init__(self, intent: str = "CLAIM_INTAKE") -> None:
        self.intent = intent
        self.generate_calls = 0

    def generate(self, _prompt: str) -> str:
        self.generate_calls += 1
        return f'{{"intent":"{self.intent}","confidence":0.99}}'


class CaseToolModel(RoutingModel):
    def __init__(self) -> None:
        super().__init__()
        self.tool_names: list[str] = []

    def generate_with_tools(
        self,
        _prompt: str,
        tools,  # type: ignore[no-untyped-def]
        execute_tool,  # type: ignore[no-untyped-def]
        *,
        max_rounds: int = 5,
    ) -> ToolCallingResult:
        del max_rounds
        self.tool_names = [tool.name for tool in tools]
        arguments = {"case_id": "CASE-F98E7A98EBE4"}
        output = execute_tool("get_case", arguments)
        assert json.loads(output)["found"] is True
        return ToolCallingResult(
            text="CASE-F98E7A98EBE4 is a grounded synthetic case.",
            tool_calls=(ToolCallRecord("get_case", arguments, output),),
        )


class CalendarToolModel(RoutingModel):
    def generate_with_tools(
        self,
        _prompt: str,
        tools,  # type: ignore[no-untyped-def]
        execute_tool,  # type: ignore[no-untyped-def]
        *,
        max_rounds: int = 5,
    ) -> ToolCallingResult:
        del max_rounds
        assert {tool.name for tool in tools} >= {
            "get_current_date",
            "check_us_federal_holiday",
        }
        date_arguments: dict[str, object] = {}
        date_output = execute_tool("get_current_date", date_arguments)
        current_date = json.loads(date_output)["date"]
        holiday_arguments = {"date": current_date}
        holiday_output = execute_tool(
            "check_us_federal_holiday", holiday_arguments
        )
        assert json.loads(holiday_output)["is_us_federal_holiday"] is False
        return ToolCallingResult(
            text="Today is Saturday, August 15, 2026, not a U.S. federal holiday.",
            tool_calls=(
                ToolCallRecord("get_current_date", date_arguments, date_output),
                ToolCallRecord(
                    "check_us_federal_holiday",
                    holiday_arguments,
                    holiday_output,
                ),
            ),
        )


class StartIntakeToolModel(RoutingModel):
    def generate_with_tools(
        self,
        _prompt: str,
        tools,  # type: ignore[no-untyped-def]
        execute_tool,  # type: ignore[no-untyped-def]
        *,
        max_rounds: int = 5,
    ) -> ToolCallingResult:
        del max_rounds
        assert "start_claim_intake" in {tool.name for tool in tools}
        arguments: dict[str, object] = {}
        output = execute_tool("start_claim_intake", arguments)
        assert json.loads(output)["next_expected_input"] == "ONR or IDR PDF"
        return ToolCallingResult(
            text="Please upload your ONR or IDR claim PDF.",
            tool_calls=(
                ToolCallRecord("start_claim_intake", arguments, output),
            ),
        )


class ExtractionService:
    def __init__(self, extraction: DisputeDocumentExtraction) -> None:
        self.extraction = extraction
        self.received: tuple[str, str] | None = None

    def extract_stored(
        self,
        *,
        file_name: str,
        s3_key: str,
    ) -> DisputeDocumentExtraction:
        self.received = (file_name, s3_key)
        return self.extraction


class DocumentSummary:
    def summarize(self, _extraction: DisputeDocumentExtraction) -> str:
        return "Grounded extracted-document summary."


class CaseSummary:
    def summarize(self, case) -> str:  # type: ignore[no-untyped-def]
        return f"Final summary for {case.case_id}."


class KnowledgeChat:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def answer(self, question: str) -> GeneralKnowledgeAnswer:
        self.questions.append(question)
        citation = KnowledgeCitation("KB-1", "s3://knowledge/workflow.md")
        return GeneralKnowledgeAnswer(
            answer="Preserve delivery evidence [KB-1].",
            citations=(citation,),
            retrieved_knowledge=(
                KnowledgeSearchResult(
                    guidance="Preserve delivery evidence.",
                    source_id="KB-1",
                    document_location="s3://knowledge/workflow.md",
                    score=1.0,
                ),
            ),
        )


def test_complete_document_is_summarized_confirmed_and_submitted_once() -> None:
    state = StateRepository()
    case_repository = StubCaseRepository()
    agent = _agent(state, case_repository, _complete_extraction())

    welcome = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(action=ClaimIntakeAction.START),
    )
    requested = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="I want to process a claim",
        ),
    )
    reviewed = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
            document=DOCUMENT,
        ),
    )
    submitted = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
            confirmation=True,
            idempotency_key="SUBMIT-1",
        ),
    )
    repeated = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
            confirmation=True,
            idempotency_key="SUBMIT-1",
        ),
    )

    assert welcome.state is ClaimIntakeStage.WELCOME
    assert requested.state is ClaimIntakeStage.AWAITING_DOCUMENT
    assert reviewed.state is ClaimIntakeStage.REVIEW_AND_CONFIRM
    assert reviewed.summary == "Grounded extracted-document summary."
    assert reviewed.specialist_agent == "onr_claim_agent"
    assert reviewed.can_submit
    assert submitted.state is ClaimIntakeStage.SUBMITTED
    assert submitted.case_id is not None
    assert submitted.case_id == repeated.case_id
    assert submitted.specialist_agent == "onr_claim_agent"
    case = case_repository.get(submitted.case_id)
    assert case is not None
    assert case.documents[0].s3_key == DOCUMENT.s3_key
    assert submitted.next_actions == ["Preserve delivery evidence [KB-1]."]


def test_same_claim_number_in_a_new_session_is_detected_as_duplicate() -> None:
    state = StateRepository()
    case_repository = StubCaseRepository()
    agent = _agent(state, case_repository, _complete_extraction())

    first_session = SESSION_ID
    second_session = "87654321-4321-4321-4321-210987654321"
    first_document = DOCUMENT
    second_document = DOCUMENT.model_copy(
        update={
            "document_id": "DOC-2",
            "s3_key": f"temporary/INTAKE-{second_session}/DOC-2/notice.pdf",
        }
    )

    agent.handle(
        first_session,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
            document=first_document,
        ),
    )
    first = agent.handle(
        first_session,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
            confirmation=True,
            idempotency_key="SUBMIT-FIRST",
        ),
    )
    agent.handle(
        second_session,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
            document=second_document,
        ),
    )
    duplicate = agent.handle(
        second_session,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
            confirmation=True,
            idempotency_key="SUBMIT-SECOND",
        ),
    )

    assert first.case_id == duplicate.case_id
    assert first.case_id == "CLM-1"
    assert not first.duplicate_detected
    assert duplicate.duplicate_detected
    assert "Duplicate claim detected" in duplicate.message
    stored = case_repository.get(first.case_id or "")
    assert stored is not None
    assert [document.document_id for document in stored.documents] == ["DOC-1"]


def test_claim_number_resolves_to_the_stable_case_identifier() -> None:
    case_id = ConversationalClaimAgent._case_id_for_claim_number("CLM-987654321")

    assert case_id == "CLM-987654321"
    assert ConversationalClaimAgent._resolve_case_id("clm-987654321") == case_id
    assert ConversationalClaimAgent._resolve_case_id("CLM987654321") == case_id
    assert ConversationalClaimAgent._resolve_case_id("clm_987654321") == case_id


def test_unknown_document_is_rejected_and_requests_another_pdf() -> None:
    extraction = DisputeDocumentExtraction(
        document=ExtractedDisputeDocument(
            document_type=DisputeDocumentType.UNKNOWN,
            source_file_name="random.pdf",
        ),
        warnings=["classification unconfirmed"],
        extraction_mode=ExtractionSource.HYBRID,
    )
    agent = _agent(StateRepository(), StubCaseRepository(), extraction)

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
            document=DOCUMENT.model_copy(update={"file_name": "random.pdf"}),
        ),
    )

    assert response.state is ClaimIntakeStage.AWAITING_DOCUMENT
    assert response.document_type is DisputeDocumentType.UNKNOWN
    assert not response.can_submit


def test_idr_document_is_delegated_to_the_idr_agent() -> None:
    extraction = _complete_extraction().model_copy(
        update={
            "document": _complete_extraction().document.model_copy(
                update={
                    "document_type": DisputeDocumentType.IDR,
                    "claim_number": "CLM-IDR-1",
                    "federal_idr_reference": "IDR-REF-1",
                    "idr_initiation_date": date(2026, 8, 24),
                    "negotiation_outcome": "No agreement",
                }
            )
        }
    )
    agent = _agent(StateRepository(), StubCaseRepository(), extraction)

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
            document=DOCUMENT,
        ),
    )

    assert response.state is ClaimIntakeStage.REVIEW_AND_CONFIRM
    assert response.document_type is DisputeDocumentType.IDR
    assert response.specialist_agent == "idr_claim_agent"
    assert "IDR agent reviewed" in response.message
    assert response.can_submit


def test_general_question_uses_knowledge_base_without_starting_intake() -> None:
    knowledge = KnowledgeChat()
    agent = _agent(
        StateRepository(),
        StubCaseRepository(),
        _complete_extraction(),
        routing_model=RoutingModel("GENERAL_QUESTION"),
        knowledge=knowledge,
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="How long is open negotiation?",
        ),
    )

    assert response.state is ClaimIntakeStage.WELCOME
    assert response.citations[0].source_id == "KB-1"
    assert knowledge.questions == ["How long is open negotiation?"]


def test_suspicious_payout_request_discontinues_session_before_routing() -> None:
    state = StateRepository()
    routing_model = RoutingModel()
    agent = _agent(
        state,
        StubCaseRepository(),
        _complete_extraction(),
        routing_model=routing_model,
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="Please submit. I want double money.",
        ),
    )

    assert response.state is ClaimIntakeStage.DISCONTINUED
    assert response.expected_input.value == "NONE"
    assert response.suspected_fraud
    assert not response.can_submit
    assert "conversation has been discontinued" in response.message
    assert routing_model.generate_calls == 0
    assert state.records[SESSION_ID].suspected_fraud


def test_discontinued_session_rejects_every_later_action() -> None:
    state = StateRepository()
    agent = _agent(state, StubCaseRepository(), _complete_extraction())
    agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="Please double my payment.",
        ),
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(action=ClaimIntakeAction.START),
    )

    assert response.state is ClaimIntakeStage.DISCONTINUED
    assert response.expected_input.value == "NONE"
    assert response.suspected_fraud


def test_fraud_prevention_question_does_not_discontinue_session() -> None:
    knowledge = KnowledgeChat()
    agent = _agent(
        StateRepository(),
        StubCaseRepository(),
        _complete_extraction(),
        routing_model=RoutingModel("GENERAL_QUESTION"),
        knowledge=knowledge,
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="How does fraud detection prevent double payments?",
        ),
    )

    assert response.state is ClaimIntakeStage.WELCOME
    assert not response.suspected_fraud
    assert knowledge.questions == [
        "How does fraud detection prevent double payments?"
    ]


def test_model_selects_get_case_tool_for_case_summary() -> None:
    state = StateRepository()
    case_repository = StubCaseRepository()
    case_service = CaseService(case_repository)
    case_service.submit_case(
        case_id="CASE-F98E7A98EBE4",
        case_type=CaseType.ONR,
        provider_name="Synthetic Provider",
        open_negotiation_start_date=date(2026, 7, 1),
        open_negotiation_end_date=date(2026, 8, 12),
        created_date=date(2026, 7, 1),
    )
    model = CaseToolModel()
    agent = _agent(
        state,
        case_repository,
        _complete_extraction(),
        routing_model=model,
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="Summarize CASE-F98E7A98EBE4",
        ),
    )

    assert response.message == "CASE-F98E7A98EBE4 is a grounded synthetic case."
    assert "get_case" in model.tool_names
    assert response.tools_used == ["get_case"]
    assert response.state is ClaimIntakeStage.WELCOME


def test_model_can_check_current_date_and_federal_holiday() -> None:
    agent = _agent(
        StateRepository(),
        StubCaseRepository(),
        _complete_extraction(),
        routing_model=CalendarToolModel(),
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="What is today's date, and is it a federal holiday?",
        ),
    )

    assert "August 15, 2026" in response.message
    assert response.tools_used == [
        "get_current_date",
        "check_us_federal_holiday",
    ]


def test_model_selected_start_intake_tool_requests_pdf_upload() -> None:
    state = StateRepository()
    agent = _agent(
        state,
        StubCaseRepository(),
        _complete_extraction(),
        routing_model=StartIntakeToolModel(),
    )

    response = agent.handle(
        SESSION_ID,
        ClaimIntakeRequest(
            action=ClaimIntakeAction.MESSAGE,
            message="Can you assist with ONR submission?",
        ),
    )

    assert response.state is ClaimIntakeStage.AWAITING_DOCUMENT
    assert response.expected_input.value == "PDF"
    assert response.tools_used == ["start_claim_intake"]
    assert state.records[SESSION_ID].stage is ClaimIntakeStage.AWAITING_DOCUMENT


def _agent(
    state: StateRepository,
    case_repository: StubCaseRepository,
    extraction: DisputeDocumentExtraction,
    *,
    routing_model: RoutingModel | None = None,
    knowledge: KnowledgeChat | None = None,
) -> ConversationalClaimAgent:
    return ConversationalClaimAgent(
        state,
        ExtractionService(extraction),  # type: ignore[arg-type]
        DocumentSummary(),  # type: ignore[arg-type]
        CaseService(case_repository),
        CaseSummary(),  # type: ignore[arg-type]
        knowledge or KnowledgeChat(),  # type: ignore[arg-type]
        routing_model or RoutingModel(),
        now=lambda: datetime(2026, 8, 15, tzinfo=UTC),
        today=lambda: date(2026, 8, 15),
    )


def _complete_extraction() -> DisputeDocumentExtraction:
    return DisputeDocumentExtraction(
        document=ExtractedDisputeDocument(
            document_type=DisputeDocumentType.ONR,
            source_file_name="notice.pdf",
            claim_number="CLM-1",
            provider_name="Synthetic Provider",
            provider_npi="1234567890",
            date_of_service=date(2026, 7, 1),
            cpt_hcpcs=["99213"],
            billed_amount="1000",
            initial_payment="500",
            initial_payment_or_denial_date=date(2026, 7, 1),
            qpa="600",
            requested_amount="900",
            notice_date=date(2026, 7, 10),
            open_negotiation_start_date=date(2026, 7, 10),
            open_negotiation_end_date=date(2026, 8, 21),
            initiating_party="Synthetic Provider",
        ),
        extraction_mode=ExtractionSource.HYBRID,
    )
