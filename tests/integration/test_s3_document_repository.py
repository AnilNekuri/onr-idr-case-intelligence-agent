"""Document repository contract checks against the real development S3 bucket."""

import os
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import pytest

from app.repositories import DocumentNotFoundError, S3DocumentRepository

pytestmark = pytest.mark.integration

PDF_CONTENT = b"%PDF-1.4\nsynthetic integration document\n%%EOF"


def test_upload_metadata_download_and_missing_file() -> None:
    if os.getenv("RUN_AWS_INTEGRATION") != "1":
        pytest.skip("Set RUN_AWS_INTEGRATION=1 to allow development AWS writes")

    bucket_name = os.getenv("S3_CASE_DOCUMENTS_BUCKET")
    if not bucket_name:
        pytest.skip("Set S3_CASE_DOCUMENTS_BUCKET to the Terraform bucket output")

    case_id = f"INTEGRATION-{uuid4()}"
    repository = S3DocumentRepository(bucket_name)
    s3_client = boto3.client("s3")
    document = repository.upload_pdf(
        case_id,
        "synthetic-notice.pdf",
        PDF_CONTENT,
        metadata={"test-purpose": "repository-contract"},
        temporary=True,
    )

    try:
        assert repository.get(document.s3_key) == PDF_CONTENT
        metadata = repository.get_metadata(document.s3_key)
        assert metadata["case-id"] == case_id
        assert metadata["document-id"] == document.document_id
        assert metadata["test-purpose"] == "repository-contract"

        with pytest.raises(DocumentNotFoundError):
            repository.get(f"temporary/{case_id}/missing.pdf")
    finally:
        s3_client.delete_object(Bucket=bucket_name, Key=document.s3_key)
