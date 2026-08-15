"""Repository contract checks against the real development DynamoDB table."""

import os
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import pytest

from app.models import CaseStatus
from app.repositories import DynamoDbCaseRepository
from tests.unit.tool_support import make_case

pytestmark = pytest.mark.integration


def test_create_read_update_and_not_found_against_development_table() -> None:
    if os.getenv("RUN_AWS_INTEGRATION") != "1":
        pytest.skip("Set RUN_AWS_INTEGRATION=1 to allow development AWS writes")

    table_name = os.getenv("DYNAMODB_CASE_TABLE")
    if not table_name:
        pytest.skip("Set DYNAMODB_CASE_TABLE to the Terraform table output")

    case_id = f"INTEGRATION-{uuid4()}"
    missing_case_id = f"MISSING-{uuid4()}"
    repository = DynamoDbCaseRepository(table_name)
    table = boto3.resource("dynamodb").Table(table_name)

    try:
        created = make_case(case_id=case_id, status=CaseStatus.NEW)
        repository.save(created)
        assert repository.get(case_id) == created

        updated = created.model_copy(update={"status": CaseStatus.COMPLETE})
        repository.save(updated)
        assert repository.get(case_id) == updated

        assert repository.get(missing_case_id) is None
    finally:
        table.delete_item(Key={"case_id": case_id})
