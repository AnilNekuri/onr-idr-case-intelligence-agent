"""Deterministic rules for identifying absent case information."""

from app.models import Case, CaseStatus
from app.repositories import CaseRepository
from app.tools.case_tool import require_case


def get_missing_information(
    repository: CaseRepository,
    case_id: str,
) -> list[str]:
    """Return explicit missing-document and missing-response markers."""
    case = require_case(repository, case_id)
    return find_missing_information(case)


def find_missing_information(case: Case) -> list[str]:
    """Return missing-evidence markers from an already retrieved case."""
    missing_information = [
        f"document:{document_name}" for document_name in case.missing_documents
    ]

    if (
        case.status is CaseStatus.PENDING_PROVIDER_RESPONSE
        and not case.provider_response_received
    ):
        missing_information.append("response:provider_response")

    return missing_information
