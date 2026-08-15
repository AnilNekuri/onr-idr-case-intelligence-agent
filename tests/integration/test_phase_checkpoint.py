"""Full deterministic Step 9 checkpoint against development AWS resources."""

import os
from datetime import date
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import pytest

from app.config import ApplicationSettings, CaseRepositoryKind
from app.repositories import create_case_repository, create_document_repository
from app.services import CaseService, DocumentService
from app.tools import DeadlineRisk
from app.workflows import run_phase_checkpoint

pytestmark = pytest.mark.integration


def test_full_phase_checkpoint_against_development_aws() -> None:
    if os.getenv("RUN_AWS_INTEGRATION") != "1":
        pytest.skip("Set RUN_AWS_INTEGRATION=1 to allow development AWS writes")

    settings = ApplicationSettings.from_environment()
    if settings.case_repository is not CaseRepositoryKind.DYNAMODB:
        pytest.skip("Set CASE_REPOSITORY=dynamodb for the AWS checkpoint")
    if settings.s3_case_documents_bucket is None:
        pytest.skip("Set S3_CASE_DOCUMENTS_BUCKET for the AWS checkpoint")
    assert settings.dynamodb_case_table is not None

    case_id = f"CHECKPOINT-INTEGRATION-{uuid4()}"
    session = boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )
    dynamodb = session.resource("dynamodb")
    s3_client = session.client("s3")

    try:
        result = run_phase_checkpoint(
            CaseService(create_case_repository(settings)),
            DocumentService(create_document_repository(settings)),
            current_date=date.today(),
            case_id=case_id,
        )

        assert result.case.case_id == case_id
        assert result.case.documents == [result.document]
        assert len(result.timeline) == 2
        assert result.missing_information == [
            "document:provider-response-form.pdf",
            "response:provider_response",
        ]
        assert result.deadline_risk.days_remaining == 7
        assert result.deadline_risk.risk is DeadlineRisk.MEDIUM
        assert (
            DocumentService(create_document_repository(settings)).get_document(
                result.document.s3_key
            )
            == b"%PDF-1.4\nsynthetic Step 9 checkpoint document\n%%EOF"
        )
    finally:
        response = s3_client.list_objects_v2(
            Bucket=settings.s3_case_documents_bucket,
            Prefix=f"temporary/{case_id}/",
        )
        for stored_object in response.get("Contents", []):
            s3_client.delete_object(
                Bucket=settings.s3_case_documents_bucket,
                Key=stored_object["Key"],
            )
        dynamodb.Table(settings.dynamodb_case_table).delete_item(
            Key={"case_id": case_id}
        )
