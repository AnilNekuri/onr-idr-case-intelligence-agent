"""Tests for the service-layer case document workflow."""

from collections.abc import Mapping
from datetime import date

import pytest

from app.models import Document
from app.services import CaseDocumentService, CaseService, DocumentService
from app.tools import CaseNotFoundError
from tests.unit.tool_support import StubCaseRepository, make_case


class RecordingDocumentRepository:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, bytes]] = []

    def upload_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: Mapping[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        self.uploads.append((case_id, file_name, content))
        return Document(
            document_id="DOC-UPLOADED",
            file_name=file_name,
            s3_key=f"cases/{case_id}/DOC-UPLOADED/{file_name}",
        )

    def get(self, s3_key: str) -> bytes:
        raise NotImplementedError

    def get_metadata(self, s3_key: str) -> dict[str, str]:
        raise NotImplementedError


def test_upload_document_stores_and_attaches_through_services() -> None:
    case = make_case(case_id="CASE-UPLOAD")
    case_repository = StubCaseRepository(case)
    document_repository = RecordingDocumentRepository()
    service = CaseDocumentService(
        CaseService(case_repository),
        DocumentService(document_repository),
    )

    updated, document = service.upload_document(
        case.case_id,
        "notice.pdf",
        b"%PDF-1.4 synthetic",
        received_date=date(2026, 8, 14),
    )

    assert document_repository.uploads == [
        ("CASE-UPLOAD", "notice.pdf", b"%PDF-1.4 synthetic")
    ]
    assert updated.documents == [document]
    assert case_repository.get(case.case_id) == updated


def test_upload_document_checks_case_before_storage() -> None:
    document_repository = RecordingDocumentRepository()
    service = CaseDocumentService(
        CaseService(StubCaseRepository()),
        DocumentService(document_repository),
    )

    with pytest.raises(CaseNotFoundError, match="CASE-MISSING"):
        service.upload_document(
            "CASE-MISSING",
            "notice.pdf",
            b"%PDF-1.4 synthetic",
            received_date=date(2026, 8, 14),
        )

    assert document_repository.uploads == []
