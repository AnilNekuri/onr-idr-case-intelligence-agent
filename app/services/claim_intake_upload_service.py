"""Store claim-intake PDFs before invoking the remote AgentCore runtime."""

from app.models import StoredIntakeDocument
from app.services.document_service import DocumentService


class ClaimIntakeUploadService:
    """Upload one temporary intake PDF and return a safe S3 reference."""

    def __init__(self, document_service: DocumentService) -> None:
        self._document_service = document_service

    def upload(
        self,
        session_id: str,
        file_name: str,
        content: bytes,
    ) -> StoredIntakeDocument:
        """Store a PDF under a session-scoped temporary prefix."""
        if len(session_id.strip()) < 33:
            raise ValueError("session_id must contain at least 33 characters")
        document = self._document_service.upload_case_pdf(
            f"INTAKE-{session_id}",
            file_name,
            content,
            metadata={"purpose": "conversational-claim-intake"},
            temporary=True,
        )
        return StoredIntakeDocument(
            document_id=document.document_id,
            file_name=document.file_name,
            s3_key=document.s3_key,
        )
