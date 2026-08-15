"""Local unit tests for the S3 document repository adapter."""

from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.repositories import (
    DocumentNotFoundError,
    DocumentRepository,
    DocumentRepositoryError,
    S3DocumentRepository,
    UnsupportedDocumentTypeError,
)

PDF_CONTENT = b"%PDF-1.4\nsynthetic test document\n%%EOF"


def client_error(code: str, operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "synthetic AWS error"}},
        operation,
    )


class FakeS3Client:
    """Small in-memory substitute for the S3 client methods under test."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.put_error: ClientError | None = None
        self.get_error: ClientError | None = None
        self.head_error: ClientError | None = None

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        if self.put_error is not None:
            raise self.put_error
        self.objects[kwargs["Key"]] = {
            "Body": kwargs["Body"],
            "ContentType": kwargs["ContentType"],
            "Metadata": kwargs["Metadata"],
        }
        return {"ETag": '"synthetic-etag"'}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.get_error is not None:
            raise self.get_error
        try:
            stored = self.objects[kwargs["Key"]]
        except KeyError as error:
            raise client_error("NoSuchKey", "GetObject") from error
        return {"Body": BytesIO(stored["Body"])}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.head_error is not None:
            raise self.head_error
        try:
            stored = self.objects[kwargs["Key"]]
        except KeyError as error:
            raise client_error("404", "HeadObject") from error
        return {
            "ContentType": stored["ContentType"],
            "Metadata": stored["Metadata"],
        }


def make_repository(
    client: FakeS3Client | None = None,
) -> tuple[S3DocumentRepository, FakeS3Client]:
    fake_client = client or FakeS3Client()
    repository = S3DocumentRepository(
        "synthetic-case-documents",
        s3_client=fake_client,
        document_id_factory=lambda: "DOC-1001",
    )
    contract_check: DocumentRepository = repository
    assert contract_check is repository
    return repository, fake_client


def test_pdf_upload_and_download() -> None:
    repository, client = make_repository()

    document = repository.upload_pdf("CASE-1001", "notice.pdf", PDF_CONTENT)

    assert document.document_id == "DOC-1001"
    assert document.file_name == "notice.pdf"
    assert repository.get(document.s3_key) == PDF_CONTENT
    assert client.objects[document.s3_key]["ContentType"] == "application/pdf"


def test_upload_stores_system_and_custom_metadata() -> None:
    repository, _ = make_repository()

    document = repository.upload_pdf(
        "CASE-1001",
        "itemized-bill.pdf",
        PDF_CONTENT,
        metadata={"source": "synthetic-provider", "category": "bill"},
    )

    assert repository.get_metadata(document.s3_key) == {
        "case-id": "CASE-1001",
        "document-id": "DOC-1001",
        "original-file-name": "itemized-bill.pdf",
        "source": "synthetic-provider",
        "category": "bill",
    }


def test_object_key_generation_sanitizes_path_components() -> None:
    repository, _ = make_repository()

    document = repository.upload_pdf(
        "CASE/1001",
        "../provider notice.pdf",
        PDF_CONTENT,
        temporary=True,
    )

    assert document.s3_key == ("temporary/CASE-1001/DOC-1001/provider-notice.pdf")


def test_missing_file_raises_document_not_found_error() -> None:
    repository, _ = make_repository()

    with pytest.raises(DocumentNotFoundError, match="Document not found"):
        repository.get("cases/CASE-1001/DOC-MISSING/missing.pdf")


@pytest.mark.parametrize(
    ("file_name", "content", "message"),
    [
        ("notice.txt", PDF_CONTENT, "Only .pdf files"),
        ("notice.pdf", b"not a PDF", "valid PDF signature"),
    ],
)
def test_unsupported_file_types_are_rejected(
    file_name: str,
    content: bytes,
    message: str,
) -> None:
    repository, client = make_repository()

    with pytest.raises(UnsupportedDocumentTypeError, match=message):
        repository.upload_pdf("CASE-1001", file_name, content)

    assert client.objects == {}


def test_failed_aws_upload_is_wrapped() -> None:
    client = FakeS3Client()
    client.put_error = client_error("AccessDenied", "PutObject")
    repository, _ = make_repository(client)

    with pytest.raises(DocumentRepositoryError, match="Failed to upload"):
        repository.upload_pdf("CASE-1001", "notice.pdf", PDF_CONTENT)


def test_failed_aws_read_is_wrapped() -> None:
    client = FakeS3Client()
    client.get_error = client_error("AccessDenied", "GetObject")
    repository, _ = make_repository(client)

    with pytest.raises(DocumentRepositoryError, match="AWS S3 request failed"):
        repository.get("cases/CASE-1001/DOC-1001/notice.pdf")
