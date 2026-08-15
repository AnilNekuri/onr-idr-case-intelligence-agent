"""Repository contract and errors for supporting-document storage."""

from collections.abc import Mapping
from typing import Protocol

from app.models import Document


class DocumentRepositoryError(RuntimeError):
    """Base error for document storage failures."""


class DocumentNotFoundError(DocumentRepositoryError):
    """Raised when a requested document object does not exist."""


class UnsupportedDocumentTypeError(ValueError):
    """Raised when an upload is not a supported PDF document."""


class DocumentRepository(Protocol):
    """Storage-independent operations required for case documents."""

    def upload_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: Mapping[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        """Validate and store one PDF, returning its identifying metadata."""
        ...

    def get(self, s3_key: str) -> bytes:
        """Return document bytes or raise ``DocumentNotFoundError``."""
        ...

    def get_metadata(self, s3_key: str) -> dict[str, str]:
        """Return user and system metadata stored with a document."""
        ...
