"""Unit test for the deterministic Step 9 phase checkpoint."""

from collections.abc import Mapping
from datetime import date

from app.models import CaseEventType, Document
from app.repositories import DocumentRepository
from app.services import CaseService, DocumentService
from app.tools import DeadlineRisk
from app.workflows import run_phase_checkpoint
from tests.unit.tool_support import StubCaseRepository


class RecordingDocumentRepository:
    """Record uploads and ensure the case was saved before document upload."""

    def __init__(self, case_repository: StubCaseRepository) -> None:
        self.case_repository = case_repository
        self.uploaded_content: bytes | None = None

    def upload_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: Mapping[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        assert self.case_repository.get(case_id) is not None
        assert metadata == {"workflow": "step-9-checkpoint"}
        assert temporary is True
        self.uploaded_content = content
        return Document(
            document_id="DOC-CHECKPOINT",
            file_name=file_name,
            s3_key=f"temporary/{case_id}/DOC-CHECKPOINT/{file_name}",
        )

    def get(self, s3_key: str) -> bytes:
        assert self.uploaded_content is not None
        return self.uploaded_content

    def get_metadata(self, s3_key: str) -> dict[str, str]:
        return {"workflow": "step-9-checkpoint"}


def test_phase_checkpoint_runs_without_an_llm() -> None:
    case_repository = StubCaseRepository()
    document_repository: DocumentRepository = RecordingDocumentRepository(
        case_repository
    )

    result = run_phase_checkpoint(
        CaseService(case_repository),
        DocumentService(document_repository),
        current_date=date(2026, 8, 13),
        case_id="CHECKPOINT-UNIT",
    )

    assert case_repository.get("CHECKPOINT-UNIT") == result.case
    assert result.case.documents == [result.document]
    assert [event.type for event in result.timeline] == [
        CaseEventType.CASE_CREATED,
        CaseEventType.DOCUMENT_RECEIVED,
    ]
    assert result.missing_information == [
        "document:provider-response-form.pdf",
        "response:provider_response",
    ]
    assert result.deadline_risk.days_remaining == 7
    assert result.deadline_risk.risk is DeadlineRisk.MEDIUM
    assert result.model_dump()["case"] == result.case.model_dump(mode="json")
