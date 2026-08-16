"""Storage contract for durable conversational claim-intake state."""

from typing import Protocol

from app.models.claim_intake import ClaimIntakeRecord


class ClaimIntakeRepository(Protocol):
    """Persist workflow state independently of an AgentCore microVM."""

    def get(self, session_id: str) -> ClaimIntakeRecord | None:
        """Return the state for one runtime session."""
        ...

    def save(self, record: ClaimIntakeRecord) -> None:
        """Create or replace one session record."""
        ...
