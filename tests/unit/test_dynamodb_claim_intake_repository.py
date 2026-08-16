"""Unit tests for durable claim-intake session state."""

from datetime import UTC, datetime
from typing import Any

from app.models import ClaimIntakeRecord, ClaimIntakeStage
from app.repositories import DynamoDbClaimIntakeRepository


class Table:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def get_item(self, **kwargs: Any) -> dict[str, object]:
        item = self.items.get(kwargs["Key"]["session_id"])
        return {} if item is None else {"Item": item}

    def put_item(self, **kwargs: Any) -> dict[str, object]:
        item = kwargs["Item"]
        self.items[item["session_id"]] = item
        return {}


class Resource:
    def __init__(self, table: Table) -> None:
        self.table = table

    def Table(self, _name: str) -> Table:  # noqa: N802
        return self.table


def test_round_trips_session_state_with_ttl() -> None:
    table = Table()
    repository = DynamoDbClaimIntakeRepository(
        "claim-intake",
        dynamodb_resource=Resource(table),
    )
    record = ClaimIntakeRecord(
        session_id="12345678-1234-1234-1234-123456789012",
        stage=ClaimIntakeStage.WELCOME,
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
        expires_at=1770000000,
    )

    repository.save(record)

    assert repository.get(record.session_id) == record
    assert table.items[record.session_id]["expires_at"] == 1770000000
