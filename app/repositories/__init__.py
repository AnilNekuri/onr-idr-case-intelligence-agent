"""Storage contracts and repository implementations."""

from app.repositories.case_repository import CaseRepository, RepositoryDataError
from app.repositories.claim_intake_repository import ClaimIntakeRepository
from app.repositories.document_repository import (
    DocumentNotFoundError,
    DocumentRepository,
    DocumentRepositoryError,
    UnsupportedDocumentTypeError,
)
from app.repositories.dynamodb_case_repository import DynamoDbCaseRepository
from app.repositories.dynamodb_claim_intake_repository import (
    DynamoDbClaimIntakeRepository,
)
from app.repositories.factory import (
    create_case_repository,
    create_claim_intake_repository,
    create_document_repository,
)
from app.repositories.in_memory_claim_intake_repository import (
    InMemoryClaimIntakeRepository,
)
from app.repositories.json_case_repository import JsonCaseRepository
from app.repositories.s3_document_repository import S3DocumentRepository

__all__ = [
    "CaseRepository",
    "ClaimIntakeRepository",
    "DynamoDbCaseRepository",
    "DynamoDbClaimIntakeRepository",
    "DocumentNotFoundError",
    "DocumentRepository",
    "DocumentRepositoryError",
    "JsonCaseRepository",
    "InMemoryClaimIntakeRepository",
    "RepositoryDataError",
    "S3DocumentRepository",
    "UnsupportedDocumentTypeError",
    "create_case_repository",
    "create_claim_intake_repository",
    "create_document_repository",
]
