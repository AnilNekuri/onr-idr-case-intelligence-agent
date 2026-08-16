"""Tests for process-local claim-intake session storage."""

from datetime import UTC, datetime

from app.models import ClaimIntakeRecord, ClaimIntakeStage
from app.repositories import InMemoryClaimIntakeRepository


def test_repository_saves_and_isolates_records() -> None:
    repository = InMemoryClaimIntakeRepository()
    session_id = "session-123456789012345678901234567890"
    record = ClaimIntakeRecord(
        session_id=session_id,
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
        expires_at=1_800_000_000,
    )

    repository.save(record)
    loaded = repository.get(session_id)

    assert loaded == record
    assert loaded is not record
    assert repository.get("missing-session") is None


def test_repository_replaces_existing_session() -> None:
    repository = InMemoryClaimIntakeRepository()
    session_id = "session-123456789012345678901234567890"
    record = ClaimIntakeRecord(
        session_id=session_id,
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
        expires_at=1_800_000_000,
    )
    repository.save(record)

    repository.save(record.model_copy(update={"stage": ClaimIntakeStage.SUBMITTED}))

    loaded = repository.get(session_id)
    assert loaded is not None
    assert loaded.stage is ClaimIntakeStage.SUBMITTED
