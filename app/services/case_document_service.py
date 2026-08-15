"""Case-document workflow composed entirely from application services."""

from collections.abc import Mapping
from datetime import date

from app.models import Case, Document
from app.services.case_service import CaseService
from app.services.document_service import DocumentService
from app.tools import CaseNotFoundError


class CaseDocumentService:
    """Upload a PDF and attach its metadata to an authoritative case."""

    def __init__(
        self,
        case_service: CaseService,
        document_service: DocumentService,
    ) -> None:
        self._case_service = case_service
        self._document_service = document_service

    def upload_document(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        received_date: date,
        metadata: Mapping[str, str] | None = None,
    ) -> tuple[Case, Document]:
        """Validate the case, store one PDF, and persist its case reference."""
        normalized_case_id = case_id.strip()
        case = self._case_service.get_case(normalized_case_id)
        if case is None:
            raise CaseNotFoundError(f"Case not found: {normalized_case_id}")

        document = self._document_service.upload_case_pdf(
            case.case_id,
            file_name,
            content,
            metadata=metadata,
        )
        updated_case = self._case_service.attach_document(
            case.case_id,
            document,
            received_date=received_date,
        )
        return updated_case, document
