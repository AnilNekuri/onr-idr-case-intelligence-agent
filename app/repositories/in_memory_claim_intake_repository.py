"""Process-local claim-intake state for the undeployed UI test path."""

from threading import Lock

from app.models import ClaimIntakeRecord


class InMemoryClaimIntakeRepository:
    """Store claim-intake sessions for the lifetime of one UI process."""

    def __init__(self) -> None:
        self._records: dict[str, ClaimIntakeRecord] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> ClaimIntakeRecord | None:
        """Return an isolated copy of one session when it exists."""
        with self._lock:
            record = self._records.get(session_id)
            return record.model_copy(deep=True) if record is not None else None

    def save(self, record: ClaimIntakeRecord) -> None:
        """Create or replace one process-local session."""
        with self._lock:
            self._records[record.session_id] = record.model_copy(deep=True)
