"""Deterministic access to authoritative case facts."""

from app.models import Case
from app.repositories import CaseRepository


class CaseNotFoundError(LookupError):
    """Raised when a derived tool requires a case that does not exist."""


def get_case(repository: CaseRepository, case_id: str) -> Case | None:
    """Retrieve a case without depending on a storage implementation."""
    return repository.get(case_id)


def require_case(repository: CaseRepository, case_id: str) -> Case:
    """Retrieve a case or raise a consistent error for derived tools."""
    case = get_case(repository, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case not found: {case_id}")
    return case
