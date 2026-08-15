"""Repository contract for authoritative case storage."""

from typing import Protocol

from app.models import Case


class RepositoryDataError(ValueError):
    """Raised when stored repository data cannot be decoded or validated."""


class CaseRepository(Protocol):
    """Storage-independent operations required by the case service."""

    def get(self, case_id: str) -> Case | None:
        """Return a case by ID, or ``None`` when it does not exist."""
        ...

    def save(self, case: Case) -> None:
        """Create or replace a case using its case ID."""
        ...
