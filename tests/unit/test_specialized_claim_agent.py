"""Tests for the dedicated ONR and IDR workflow agents."""

import pytest

from app.models import (
    CaseType,
    DisputeDocumentExtraction,
    DisputeDocumentType,
    ExtractedDisputeDocument,
    ExtractionSource,
)
from app.services import CaseSummaryService, DocumentSummaryService
from app.services.knowledge_chat_service import (
    GeneralKnowledgeAnswer,
    KnowledgeCitation,
)
from app.services.specialized_claim_agent import IdrClaimAgent, OnrClaimAgent
from tests.unit.tool_support import make_case


class SummaryModel:
    def generate(self, _prompt: str) -> str:
        return "Grounded specialist summary."


class KnowledgeChat:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def answer(self, question: str) -> GeneralKnowledgeAnswer:
        self.questions.append(question)
        return GeneralKnowledgeAnswer(
            answer="Grounded next action [KB-1].",
            citations=(KnowledgeCitation("KB-1", "s3://knowledge/source.md"),),
            retrieved_knowledge=(),
        )


def _agents() -> tuple[OnrClaimAgent, IdrClaimAgent, KnowledgeChat]:
    model = SummaryModel()
    knowledge = KnowledgeChat()
    services = (
        DocumentSummaryService(model),  # type: ignore[arg-type]
        CaseSummaryService(model),  # type: ignore[arg-type]
        knowledge,
    )
    return (
        OnrClaimAgent(*services),  # type: ignore[arg-type]
        IdrClaimAgent(*services),  # type: ignore[arg-type]
        knowledge,
    )


def _extraction(document_type: DisputeDocumentType) -> DisputeDocumentExtraction:
    return DisputeDocumentExtraction(
        document=ExtractedDisputeDocument(
            document_type=document_type,
            source_file_name="claim.pdf",
            claim_number="CLM-1",
        ),
        extraction_mode=ExtractionSource.HYBRID,
    )


def test_onr_agent_reviews_onr_and_rejects_idr() -> None:
    onr_agent, _, _ = _agents()

    review = onr_agent.review(_extraction(DisputeDocumentType.ONR))

    assert review.agent_name == "onr_claim_agent"
    assert "negotiation notice" in review.next_actions[0]
    with pytest.raises(ValueError, match="cannot process IDR"):
        onr_agent.review(_extraction(DisputeDocumentType.IDR))


def test_idr_agent_completes_only_idr_cases_with_grounded_guidance() -> None:
    _, idr_agent, knowledge = _agents()
    idr_case = make_case().model_copy(update={"case_type": CaseType.IDR})

    result = idr_agent.complete_submission(idr_case)

    assert result.agent_name == "idr_claim_agent"
    assert result.summary == "Grounded specialist summary."
    assert result.next_actions == ("Grounded next action [KB-1].",)
    assert "Federal IDR" in knowledge.questions[0]
    with pytest.raises(ValueError, match="cannot process ONR"):
        idr_agent.complete_submission(make_case())
