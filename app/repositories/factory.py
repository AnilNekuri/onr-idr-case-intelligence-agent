"""Composition helpers that select concrete repositories from configuration."""

from app.config import ApplicationSettings, CaseRepositoryKind, ConfigurationError
from app.repositories.case_repository import CaseRepository
from app.repositories.claim_intake_repository import ClaimIntakeRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.dynamodb_case_repository import DynamoDbCaseRepository
from app.repositories.dynamodb_claim_intake_repository import (
    DynamoDbClaimIntakeRepository,
)
from app.repositories.json_case_repository import JsonCaseRepository
from app.repositories.s3_document_repository import S3DocumentRepository


def create_case_repository(settings: ApplicationSettings) -> CaseRepository:
    """Construct the configured authoritative case repository."""
    if settings.case_repository is CaseRepositoryKind.JSON:
        return JsonCaseRepository(settings.json_cases_path)

    if settings.dynamodb_case_table is None:
        raise ConfigurationError(
            "DYNAMODB_CASE_TABLE is required when CASE_REPOSITORY=dynamodb"
        )
    return DynamoDbCaseRepository(
        settings.dynamodb_case_table,
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )


def create_document_repository(settings: ApplicationSettings) -> DocumentRepository:
    """Construct S3 document storage for the configured development bucket."""
    if settings.s3_case_documents_bucket is None:
        raise ConfigurationError(
            "S3_CASE_DOCUMENTS_BUCKET is required for document uploads"
        )
    return S3DocumentRepository(
        settings.s3_case_documents_bucket,
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )


def create_claim_intake_repository(
    settings: ApplicationSettings,
) -> ClaimIntakeRepository:
    """Construct durable DynamoDB-backed claim-intake state."""
    if settings.claim_intake_table is None:
        raise ConfigurationError(
            "CLAIM_INTAKE_TABLE is required for conversational claim intake"
        )
    return DynamoDbClaimIntakeRepository(
        settings.claim_intake_table,
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )
