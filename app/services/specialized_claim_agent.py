"""Dedicated ONR and IDR agents called by the conversational coordinator."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.models import (
    Case,
    CaseType,
    ClaimRuleEvaluation,
    ClaimRuleStatus,
    DisputeDocumentExtraction,
    DisputeDocumentType,
)
from app.services.case_summary_service import CaseSummaryService
from app.services.document_summary_service import DocumentSummaryService
from app.services.knowledge_chat_service import (
    KnowledgeChatService,
    KnowledgeCitation,
)
from app.tools import add_us_federal_business_days

_CMS_IDR_OVERVIEW = (
    "https://www.cms.gov/nosurprises/help-resolve-payment-disputes/"
    "payment-disputes-between-providers-and-health-plans"
)
_CMS_IDR_GUIDANCE = (
    "https://www.cms.gov/files/document/"
    "federal-independent-dispute-resolution-guidance-disputing-parties.pdf"
)


@dataclass(frozen=True, slots=True)
class SpecialistReview:
    """A specialist agent's review of one extracted claim document."""

    agent_name: str
    summary: str
    message: str
    next_actions: tuple[str, ...]
    rule_evaluations: tuple[ClaimRuleEvaluation, ...]
    can_submit: bool


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
        rule_evaluations = self.evaluate_rules(extraction)
        rule_issues = tuple(
            rule.message
            for rule in rule_evaluations
            if rule.status is not ClaimRuleStatus.PASS
        )
        missing_actions = tuple(
                f"Provide or verify {field.replace('_', ' ')}."
                for field in extraction.missing_fields
            )
        can_submit = not missing_actions and not rule_issues
        if not can_submit:
            next_actions = missing_actions + rule_issues
            message = (
                f"The {self.document_type.value} agent reviewed the claim. "
                "Resolve the rule or data issues before submitting it."
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
            rule_evaluations=rule_evaluations,
            can_submit=can_submit,
        )

    def evaluate_rules(
        self,
        extraction: DisputeDocumentExtraction,
    ) -> tuple[ClaimRuleEvaluation, ...]:
        """Evaluate rules owned by the concrete specialist."""
        raise NotImplementedError

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

    def evaluate_rules(
        self,
        extraction: DisputeDocumentExtraction,
    ) -> tuple[ClaimRuleEvaluation, ...]:
        """Evaluate ONR initiation, sequencing, and negotiation-period rules."""
        self._require_document_type(extraction)
        document = extraction.document
        return (
            _deadline_rule(
                rule_id="ONR_INITIATION_WITHIN_30_BUSINESS_DAYS",
                description=(
                    "Open negotiation must be initiated within 30 Federal "
                    "business days of initial payment or notice of denial."
                ),
                source=_CMS_IDR_GUIDANCE,
                anchor=document.initial_payment_or_denial_date,
                actual=document.open_negotiation_start_date,
                business_days=30,
                require_after_anchor=False,
            ),
            _exact_deadline_rule(
                rule_id="ONR_PERIOD_IS_30_BUSINESS_DAYS",
                description="The open-negotiation period lasts 30 business days.",
                source=_CMS_IDR_OVERVIEW,
                anchor=document.open_negotiation_start_date,
                actual=document.open_negotiation_end_date,
                business_days=30,
            ),
            _sequence_rule(
                rule_id="ONR_SERVICE_PRECEDES_NEGOTIATION",
                description=(
                    "The date of service must precede the open-negotiation start; "
                    "it is not the 30-business-day deadline anchor."
                ),
                source=_CMS_IDR_GUIDANCE,
                earlier=document.date_of_service,
                later=document.open_negotiation_start_date,
            ),
        )

    def _require_document_type(
        self,
        extraction: DisputeDocumentExtraction,
    ) -> None:
        if extraction.document.document_type is not self.document_type:
            raise ValueError(
                f"{self.agent_name} cannot process "
                f"{extraction.document.document_type.value} documents"
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

    def evaluate_rules(
        self,
        extraction: DisputeDocumentExtraction,
    ) -> tuple[ClaimRuleEvaluation, ...]:
        """Evaluate exhaustion of ONR and the Federal IDR initiation window."""
        actual_type = extraction.document.document_type
        if actual_type is not self.document_type:
            raise ValueError(
                f"{self.agent_name} cannot process {actual_type.value} documents"
            )
        document = extraction.document
        return (
            _exact_deadline_rule(
                rule_id="IDR_REQUIRES_30_BUSINESS_DAY_ONR_PERIOD",
                description=(
                    "The full 30-business-day open-negotiation period must end "
                    "before Federal IDR initiation."
                ),
                source=_CMS_IDR_OVERVIEW,
                anchor=document.open_negotiation_start_date,
                actual=document.open_negotiation_end_date,
                business_days=30,
            ),
            _deadline_rule(
                rule_id="IDR_INITIATION_WITHIN_4_BUSINESS_DAYS",
                description=(
                    "Federal IDR must be initiated within 4 business days after "
                    "the open-negotiation period ends."
                ),
                source=_CMS_IDR_OVERVIEW,
                anchor=document.open_negotiation_end_date,
                actual=document.idr_initiation_date,
                business_days=4,
                require_after_anchor=True,
            ),
        )


def _deadline_rule(
    *,
    rule_id: str,
    description: str,
    source: str,
    anchor: date | None,
    actual: date | None,
    business_days: int,
    require_after_anchor: bool,
) -> ClaimRuleEvaluation:
    if anchor is None or actual is None:
        return ClaimRuleEvaluation(
            rule_id=rule_id,
            status=ClaimRuleStatus.NOT_EVALUATED,
            description=description,
            source=source,
            anchor_date=anchor,
            actual_date=actual,
            message=(
                f"{rule_id} could not be evaluated because a required date "
                "is missing."
            ),
        )
    deadline = add_us_federal_business_days(anchor, business_days)
    after_anchor = actual > anchor if require_after_anchor else actual >= anchor
    passed = after_anchor and actual <= deadline
    return ClaimRuleEvaluation(
        rule_id=rule_id,
        status=ClaimRuleStatus.PASS if passed else ClaimRuleStatus.FAIL,
        description=description,
        source=source,
        anchor_date=anchor,
        calculated_deadline=deadline,
        actual_date=actual,
        message=(
            f"{rule_id} passed: {actual.isoformat()} is within the deadline "
            f"{deadline.isoformat()}."
            if passed
            else (
                f"{rule_id} failed: {actual.isoformat()} is outside the allowed "
                f"window ending {deadline.isoformat()}."
            )
        ),
    )


def _exact_deadline_rule(
    *,
    rule_id: str,
    description: str,
    source: str,
    anchor: date | None,
    actual: date | None,
    business_days: int,
) -> ClaimRuleEvaluation:
    if anchor is None or actual is None:
        return ClaimRuleEvaluation(
            rule_id=rule_id,
            status=ClaimRuleStatus.NOT_EVALUATED,
            description=description,
            source=source,
            anchor_date=anchor,
            actual_date=actual,
            message=(
                f"{rule_id} could not be evaluated because a required date "
                "is missing."
            ),
        )
    deadline = add_us_federal_business_days(anchor, business_days)
    passed = actual == deadline
    return ClaimRuleEvaluation(
        rule_id=rule_id,
        status=ClaimRuleStatus.PASS if passed else ClaimRuleStatus.FAIL,
        description=description,
        source=source,
        anchor_date=anchor,
        calculated_deadline=deadline,
        actual_date=actual,
        message=(
            f"{rule_id} passed: the recorded date matches {deadline.isoformat()}."
            if passed
            else (
                f"{rule_id} failed: expected {deadline.isoformat()}, but the "
                f"recorded date is {actual.isoformat()}."
            )
        ),
    )


def _sequence_rule(
    *,
    rule_id: str,
    description: str,
    source: str,
    earlier: date | None,
    later: date | None,
) -> ClaimRuleEvaluation:
    if earlier is None or later is None:
        return ClaimRuleEvaluation(
            rule_id=rule_id,
            status=ClaimRuleStatus.NOT_EVALUATED,
            description=description,
            source=source,
            anchor_date=earlier,
            actual_date=later,
            message=(
                f"{rule_id} could not be evaluated because a required date "
                "is missing."
            ),
        )
    passed = earlier < later
    return ClaimRuleEvaluation(
        rule_id=rule_id,
        status=ClaimRuleStatus.PASS if passed else ClaimRuleStatus.FAIL,
        description=description,
        source=source,
        anchor_date=earlier,
        actual_date=later,
        message=(
            f"{rule_id} passed: the service date precedes negotiation."
            if passed
            else f"{rule_id} failed: the service date must precede negotiation."
        ),
    )
