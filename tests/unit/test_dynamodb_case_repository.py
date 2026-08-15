"""Local unit tests for the DynamoDB case repository adapter."""

from typing import Any

import pytest

from app.models import CaseStatus
from app.repositories import (
    CaseRepository,
    DynamoDbCaseRepository,
    RepositoryDataError,
)
from tests.unit.tool_support import make_case


class FakeTable:
    """Minimal in-memory substitute for the boto3 DynamoDB Table resource."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.last_consistent_read: bool | None = None

    def get_item(
        self,
        *,
        Key: dict[str, str],
        ConsistentRead: bool,
    ) -> dict[str, Any]:
        self.last_consistent_read = ConsistentRead
        item = self.items.get(Key["case_id"])
        return {} if item is None else {"Item": item}

    def put_item(self, *, Item: dict[str, Any]) -> dict[str, Any]:
        self.items[Item["case_id"]] = Item
        return {}


class FakeDynamoDbResource:
    def __init__(self, table: FakeTable) -> None:
        self.table = table
        self.requested_table_name: str | None = None

    def Table(self, table_name: str) -> FakeTable:  # noqa: N802
        self.requested_table_name = table_name
        return self.table


def make_repository() -> tuple[DynamoDbCaseRepository, FakeTable]:
    table = FakeTable()
    resource = FakeDynamoDbResource(table)
    repository = DynamoDbCaseRepository(
        "development-cases",
        dynamodb_resource=resource,
    )
    contract_check: CaseRepository = repository
    assert contract_check is repository
    assert resource.requested_table_name == "development-cases"
    return repository, table


def test_save_and_get_round_trip() -> None:
    repository, table = make_repository()
    expected_case = make_case(case_id="CASE-DDB-1001")

    repository.save(expected_case)

    assert repository.get(expected_case.case_id) == expected_case
    assert table.last_consistent_read is True


def test_save_replaces_existing_case() -> None:
    repository, _ = make_repository()
    original = make_case(case_id="CASE-DDB-1002", status=CaseStatus.NEW)
    updated = original.model_copy(update={"status": CaseStatus.COMPLETE})

    repository.save(original)
    repository.save(updated)

    assert repository.get(original.case_id) == updated


def test_unknown_case_returns_none() -> None:
    repository, _ = make_repository()

    assert repository.get("CASE-UNKNOWN") is None


def test_invalid_stored_item_raises_repository_data_error() -> None:
    repository, table = make_repository()
    table.items["CASE-INVALID"] = {"case_id": "CASE-INVALID"}

    with pytest.raises(RepositoryDataError, match="Invalid case data"):
        repository.get("CASE-INVALID")


def test_empty_table_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="table_name must not be empty"):
        DynamoDbCaseRepository(" ", dynamodb_resource=FakeDynamoDbResource(FakeTable()))
