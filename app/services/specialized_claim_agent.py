"""Dedicated ONR and IDR agents called by the conversational coordinator."""

from dataclasses import dataclass
from typing import Protocol

from app.models import Case, CaseType, DisputeDocumentExtraction, DisputeDocumentType
from app.services.case_summary_service import CaseSummaryService
from app.services.document_summary_service import DocumentSummaryService
from app.services.knowledge_chat_service import (
    KnowledgeChatService,
    KnowledgeCitation,
)


@dataclass(frozen=True, slots=True)
class SpecialistReview:
    """A specialist agent's review of one extracted claim document."""

    agent_name: str
    summary: str
    message: str
    next_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialistSubmission:
    """Grounded specialist output after a case has been submitted."""

    agent_name: str
    summary: str
    next_actions: tuple[str, ...]
    citations: tuple[KnowledgeCitation, ...]


class SpecializedClaimAgent(Protocol):
    """Contract used by the conversational agent to call a specialist."""

    agent_name: str
    document_type: DisputeDocumentType

    def review(self, extraction: DisputeDocumentExtraction) -> SpecialistReview:
        """Review one classified extraction before submission."""
        ...

    def complete_submission(self, case: Case) -> SpecialistSubmission:
        """Summarize a submitted case and return grounded next actions."""
        ...


class _BaseSpecializedClaimAgent:
    """Shared mechanics with type-specific behavior supplied by subclasses."""

    agent_name: str
    document_type: DisputeDocumentType
    case_type: CaseType
    workflow_actions: tuple[str, ...]
    guidance_question: str

    def __init__(
        self,
        document_summary_service: DocumentSummaryService,
        case_summary_service: CaseSummaryService,
        knowledge_chat_service: KnowledgeChatService,
    ) -> None:
        self._document_summary_service = document_summary_service
        self._case_summary_service = case_summary_service
        self._knowledge_chat_service = knowledge_chat_service

    def review(self, extraction: DisputeDocumentExtraction) -> SpecialistReview:
        """Validate the handoff and perform type-specific review orchestration."""
        actual_type = extraction.document.document_type
        if actual_type is not self.document_type:
            raise ValueError(
                f"{self.agent_name} cannot process {actual_type.value} documents"
            )

        summary = self._document_summary_service.summarize(extraction)
        if extraction.missing_fields:
            next_actions = tuple(
                f"Provide or verify {field.replace('_', ' ')}."
                for field in extraction.missing_fields
            )
            message = (
                f"The {self.document_type.value} agent reviewed the claim. "
                "Complete the missing information before submitting it."
            )
        else:
            next_actions = self.workflow_actions
            message = (
                f"The {self.document_type.value} agent reviewed the claim. "
                "Review the extracted information. Would you like to submit it?"
            )
        return SpecialistReview(
            agent_name=self.agent_name,
            summary=summary,
            message=message,
            next_actions=next_actions,
        )

    def complete_submission(self, case: Case) -> SpecialistSubmission:
        """Produce the specialist's grounded post-submission output."""
        if case.case_type is not self.case_type:
            raise ValueError(
                f"{self.agent_name} cannot process {case.case_type.value} cases"
            )
        summary = self._case_summary_service.summarize(case)
        guidance = self._knowledge_chat_service.answer(self.guidance_question)
        return SpecialistSubmission(
            agent_name=self.agent_name,
            summary=summary,
            next_actions=(guidance.answer,),
            citations=guidance.citations,
        )


class OnrClaimAgent(_BaseSpecializedClaimAgent):
    """Specialist responsible for open-negotiation claim workflow."""

    agent_name = "onr_claim_agent"
    document_type = DisputeDocumentType.ONR
    case_type = CaseType.ONR
    workflow_actions = (
        "Verify the negotiation notice and delivery evidence.",
        "Track the open-negotiation period through its recorded end date.",
    )
    guidance_question = (
        "What are the next grounded actions after submitting an ONR claim?"
    )


class IdrClaimAgent(_BaseSpecializedClaimAgent):
    """Specialist responsible for Federal IDR claim workflow."""

    agent_name = "idr_claim_agent"
    document_type = DisputeDocumentType.IDR
    case_type = CaseType.IDR
    workflow_actions = (
        "Verify the Federal IDR reference and initiation notice.",
        "Track entity selection, offers, fees, and determination milestones.",
    )
    guidance_question = (
        "What are the next grounded actions after submitting a Federal IDR claim?"
    )
