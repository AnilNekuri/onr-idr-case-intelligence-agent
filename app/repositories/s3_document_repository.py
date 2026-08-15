"""Amazon S3 implementation of supporting-document storage."""

import re
from collections.abc import Callable, Mapping
from typing import Any, NoReturn
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)

from app.models import Document
from app.repositories.document_repository import (
    DocumentNotFoundError,
    DocumentRepositoryError,
    UnsupportedDocumentTypeError,
)

_PDF_CONTENT_TYPE = "application/pdf"
_PDF_SIGNATURE = b"%PDF-"
_SAFE_COMPONENT_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_METADATA_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RESERVED_METADATA_KEYS = {"case-id", "document-id", "original-file-name"}
_MISSING_ERROR_CODES = {"404", "NoSuchKey", "NotFound"}


class S3DocumentRepository:
    """Store private case PDF files and their metadata in one S3 bucket."""

    def __init__(
        self,
        bucket_name: str,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        s3_client: Any | None = None,
        document_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not bucket_name.strip():
            raise ValueError("bucket_name must not be empty")

        if s3_client is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            s3_client = session.client("s3")

        self._bucket_name = bucket_name
        self._s3_client = s3_client
        self._document_id_factory = document_id_factory or (lambda: str(uuid4()))

    def upload_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: Mapping[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        """Validate and upload a PDF using a collision-resistant object key."""
        self._validate_pdf(file_name, content)
        document_id = self._document_id_factory()
        s3_key = self.build_object_key(
            case_id,
            document_id,
            file_name,
            temporary=temporary,
        )
        object_metadata = self._build_metadata(
            case_id,
            document_id,
            file_name,
            metadata,
        )

        try:
            self._s3_client.put_object(
                Bucket=self._bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=_PDF_CONTENT_TYPE,
                Metadata=object_metadata,
            )
        except (BotoCoreError, ClientError) as error:
            raise DocumentRepositoryError(
                f"Failed to upload document to s3://{self._bucket_name}/{s3_key}"
            ) from error

        return Document(
            document_id=document_id,
            file_name=file_name,
            s3_key=s3_key,
        )

    def get(self, s3_key: str) -> bytes:
        """Download one document, distinguishing absence from other AWS errors."""
        try:
            response = self._s3_client.get_object(
                Bucket=self._bucket_name,
                Key=s3_key,
            )
            content = response["Body"].read()
        except ClientError as error:
            self._raise_client_error(error, s3_key)
        except (BotoCoreError, KeyError, OSError) as error:
            raise DocumentRepositoryError(
                f"Failed to read document from s3://{self._bucket_name}/{s3_key}"
            ) from error

        if not isinstance(content, bytes):
            raise DocumentRepositoryError(
                f"S3 returned non-bytes content for key {s3_key!r}"
            )
        return content

    def get_metadata(self, s3_key: str) -> dict[str, str]:
        """Return the S3 user metadata associated with one document."""
        try:
            response = self._s3_client.head_object(
                Bucket=self._bucket_name,
                Key=s3_key,
            )
        except ClientError as error:
            self._raise_client_error(error, s3_key)
        except BotoCoreError as error:
            raise DocumentRepositoryError(
                f"Failed to read metadata from s3://{self._bucket_name}/{s3_key}"
            ) from error

        raw_metadata = response.get("Metadata", {})
        return {str(key): str(value) for key, value in raw_metadata.items()}

    @classmethod
    def build_object_key(
        cls,
        case_id: str,
        document_id: str,
        file_name: str,
        *,
        temporary: bool = False,
    ) -> str:
        """Build a safe S3 key without trusting user-controlled path segments."""
        prefix = "temporary" if temporary else "cases"
        safe_case_id = cls._safe_component(case_id, "case_id")
        safe_document_id = cls._safe_component(document_id, "document_id")
        base_file_name = re.split(r"[/\\]", file_name)[-1]
        safe_file_name = cls._safe_component(base_file_name, "file_name")
        return f"{prefix}/{safe_case_id}/{safe_document_id}/{safe_file_name}"

    @staticmethod
    def _validate_pdf(file_name: str, content: bytes) -> None:
        if not file_name.lower().endswith(".pdf"):
            raise UnsupportedDocumentTypeError("Only .pdf files are supported")
        if not content.startswith(_PDF_SIGNATURE):
            raise UnsupportedDocumentTypeError(
                "The uploaded file does not have a valid PDF signature"
            )

    @staticmethod
    def _safe_component(value: str, field_name: str) -> str:
        cleaned = _SAFE_COMPONENT_PATTERN.sub("-", value.strip()).strip(".-")
        if not cleaned:
            raise ValueError(f"{field_name} must contain a safe path character")
        return cleaned

    @staticmethod
    def _build_metadata(
        case_id: str,
        document_id: str,
        file_name: str,
        custom_metadata: Mapping[str, str] | None,
    ) -> dict[str, str]:
        result = {
            "case-id": case_id,
            "document-id": document_id,
            "original-file-name": file_name,
        }
        for key, value in (custom_metadata or {}).items():
            normalized_key = key.lower()
            if not _METADATA_KEY_PATTERN.fullmatch(normalized_key):
                raise ValueError(
                    "Metadata keys must contain lowercase letters, numbers, or hyphens"
                )
            if normalized_key in _RESERVED_METADATA_KEYS:
                raise ValueError(f"Metadata key {normalized_key!r} is reserved")
            if not isinstance(value, str):
                raise TypeError("Metadata values must be strings")
            result[normalized_key] = value
        return result

    def _raise_client_error(self, error: ClientError, s3_key: str) -> NoReturn:
        error_code = str(error.response.get("Error", {}).get("Code", ""))
        if error_code in _MISSING_ERROR_CODES:
            raise DocumentNotFoundError(
                f"Document not found: s3://{self._bucket_name}/{s3_key}"
            ) from error
        raise DocumentRepositoryError(
            f"AWS S3 request failed for s3://{self._bucket_name}/{s3_key}"
        ) from error
