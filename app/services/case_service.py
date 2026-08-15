"""Application service coordinating case storage and deterministic tools."""

from collections.abc import Callable
from datetime import date
from uuid import uuid4

from app.models import (
    Case,
    CaseEvent,
    CaseEventType,
    CaseStatus,
    CaseType,
    Document,
)
from app.repositories import CaseRepository
from app.tools import (
    CaseNotFoundError,
    DeadlineRiskResult,
    calculate_deadline_risk,
    get_case,
    get_case_timeline,
    get_missing_information,
)


class CaseAlreadyExistsError(ValueError):
    """Raised when intake would replace an existing authoritative case."""


class CaseService:
    """Provide case use cases through a storage-independent interface."""

    def __init__(
        self,
        repository: CaseRepository,
        *,
        case_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._case_id_factory = case_id_factory or (
            lambda: f"CASE-{uuid4().hex[:12].upper()}"
        )

    def submit_case(
        self,
        *,
        case_type: CaseType,
        provider_name: str,
        open_negotiation_start_date: date,
        open_negotiation_end_date: date,
        created_date: date,
        case_id: str | None = None,
        missing_documents: list[str] | None = None,
        additional_notes: str | None = None,
    ) -> Case:
        """Validate intake, apply creation rules, and persist one new case."""
        resolved_case_id = case_id.strip() if case_id else self._case_id_factory()
        if not resolved_case_id:
            raise ValueError("Generated case_id must not be empty")
        if self._repository.get(resolved_case_id) is not None:
            raise CaseAlreadyExistsError(f"Case already exists: {resolved_case_id}")

        resolved_missing_documents = missing_documents or []
        initial_status = (
            CaseStatus.INCOMPLETE if resolved_missing_documents else CaseStatus.NEW
        )
        case = Case(
            case_id=resolved_case_id,
            case_type=case_type,
            status=initial_status,
            created_date=created_date,
            open_negotiation_start_date=open_negotiation_start_date,
            open_negotiation_end_date=open_negotiation_end_date,
            provider_name=provider_name,
            missing_documents=resolved_missing_documents,
            events=[
                CaseEvent(
                    date=created_date,
                    type=CaseEventType.CASE_CREATED,
                    description=f"{case_type.value} case created",
                )
            ],
            additional_notes=additional_notes,
        )
        return self.create_case(case)

    def create_case(self, case: Case) -> Case:
        """Persist a validated case and return it to the caller."""
        self._repository.save(case)
        return case

    def update_case(self, case: Case) -> Case:
        """Replace the authoritative record for an existing case ID."""
        self._repository.save(case)
        return case

    def attach_document(
        self,
        case_id: str,
        document: Document,
        *,
        received_date: date,
    ) -> Case:
        """Attach uploaded document metadata and its event to a case."""
        case = self.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case not found: {case_id}")
        if any(item.document_id == document.document_id for item in case.documents):
            raise ValueError(
                f"Document already attached to case: {document.document_id}"
            )

        updated = case.model_copy(
            update={
                "documents": [*case.documents, document],
                "events": [
                    *case.events,
                    CaseEvent(
                        date=received_date,
                        type=CaseEventType.DOCUMENT_RECEIVED,
                        description=f"Document uploaded: {document.file_name}",
                    ),
                ],
            }
        )
        return self.update_case(updated)

    def get_case(self, case_id: str) -> Case | None:
        """Return authoritative case facts or ``None`` when not found."""
        return get_case(self._repository, case_id)

    def get_timeline(self, case_id: str) -> list[CaseEvent]:
        """Return the case timeline in chronological order."""
        return get_case_timeline(self._repository, case_id)

    def get_missing_information(self, case_id: str) -> list[str]:
        """Return deterministic missing-information markers for a case."""
        return get_missing_information(self._repository, case_id)

    def get_deadline_risk(
        self,
        case_id: str,
        *,
        current_date: date,
    ) -> DeadlineRiskResult:
        """Return deadline risk relative to an explicitly supplied date."""
        return calculate_deadline_risk(
            self._repository,
            case_id,
            current_date=current_date,
        )
