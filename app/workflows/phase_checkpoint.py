"""Deterministic end-to-end data-layer checkpoint with no LLM dependency."""

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

from app.models import (
    Case,
    CaseEvent,
    CaseEventType,
    CaseStatus,
    CaseType,
    Document,
)
from app.services import CaseService, DocumentService
from app.tools import DeadlineRiskResult

SYNTHETIC_PDF = b"%PDF-1.4\nsynthetic Step 9 checkpoint document\n%%EOF"


@dataclass(frozen=True, slots=True)
class PhaseCheckpointResult:
    """Evidence returned after the deterministic data-layer flow succeeds."""

    case: Case
    document: Document
    timeline: list[CaseEvent]
    missing_information: list[str]
    deadline_risk: DeadlineRiskResult

    def model_dump(self) -> dict[str, object]:
        """Return a JSON-compatible checkpoint summary."""
        return {
            "case": self.case.model_dump(mode="json"),
            "document": self.document.model_dump(mode="json"),
            "timeline": [event.model_dump(mode="json") for event in self.timeline],
            "missing_information": self.missing_information,
            "deadline_risk": {
                "deadline": self.deadline_risk.deadline.isoformat(),
                "days_remaining": self.deadline_risk.days_remaining,
                "risk": self.deadline_risk.risk.value,
            },
        }


def run_phase_checkpoint(
    case_service: CaseService,
    document_service: DocumentService,
    *,
    current_date: date,
    case_id: str | None = None,
) -> PhaseCheckpointResult:
    """Run the Step 9 create, upload, retrieve, and analysis sequence."""
    resolved_case_id = case_id or f"CHECKPOINT-{uuid4()}"
    initial_case = Case(
        case_id=resolved_case_id,
        case_type=CaseType.ONR,
        status=CaseStatus.PENDING_PROVIDER_RESPONSE,
        created_date=current_date,
        open_negotiation_start_date=current_date,
        open_negotiation_end_date=current_date + timedelta(days=7),
        provider_name="Synthetic Step 9 Provider",
        provider_response_received=False,
        missing_documents=["provider-response-form.pdf"],
        events=[
            CaseEvent(
                date=current_date,
                type=CaseEventType.CASE_CREATED,
                description="Synthetic Step 9 case created",
            )
        ],
        additional_notes="Synthetic data only; no PHI or PII.",
    )

    # Save before uploading to prove that the configured case repository works.
    case_service.create_case(initial_case)
    document = document_service.upload_case_pdf(
        initial_case.case_id,
        "synthetic-initial-notice.pdf",
        SYNTHETIC_PDF,
        metadata={"workflow": "step-9-checkpoint"},
        temporary=True,
    )
    updated_case = Case.model_validate(
        {
            **initial_case.model_dump(mode="python"),
            "documents": [document],
            "events": [
                *initial_case.events,
                CaseEvent(
                    date=current_date,
                    type=CaseEventType.DOCUMENT_RECEIVED,
                    description="Synthetic initial notice uploaded",
                ),
            ],
        }
    )
    case_service.update_case(updated_case)

    retrieved_case = case_service.get_case(updated_case.case_id)
    if retrieved_case is None:
        raise RuntimeError(
            f"Checkpoint case was not found after save: {updated_case.case_id}"
        )

    return PhaseCheckpointResult(
        case=retrieved_case,
        document=document,
        timeline=case_service.get_timeline(retrieved_case.case_id),
        missing_information=case_service.get_missing_information(
            retrieved_case.case_id
        ),
        deadline_risk=case_service.get_deadline_risk(
            retrieved_case.case_id,
            current_date=current_date,
        ),
    )
