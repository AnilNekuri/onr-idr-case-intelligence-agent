"""Application service for storage-independent document operations."""

from collections.abc import Mapping

from app.models import Document
from app.repositories import DocumentRepository


class DocumentService:
    """Coordinate document use cases through the repository contract."""

    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def upload_case_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: Mapping[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        """Upload one validated case PDF and return its identifier."""
        return self._repository.upload_pdf(
            case_id,
            file_name,
            content,
            metadata=metadata,
            temporary=temporary,
        )

    def get_document(self, s3_key: str) -> bytes:
        """Retrieve document bytes by storage key."""
        return self._repository.get(s3_key)

    def get_document_metadata(self, s3_key: str) -> dict[str, str]:
        """Retrieve stored document metadata by storage key."""
        return self._repository.get_metadata(s3_key)
