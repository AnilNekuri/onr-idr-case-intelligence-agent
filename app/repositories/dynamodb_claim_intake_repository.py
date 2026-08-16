"""DynamoDB implementation of conversational claim-intake state."""

import json
from decimal import Decimal
from typing import Any

import boto3  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.models.claim_intake import ClaimIntakeRecord
from app.repositories.case_repository import RepositoryDataError


class DynamoDbClaimIntakeRepository:
    """Store each intake session as one item keyed by ``session_id``."""

    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if not table_name.strip():
            raise ValueError("table_name must not be empty")
        if dynamodb_resource is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            dynamodb_resource = session.resource("dynamodb")
        self._table = dynamodb_resource.Table(table_name)

    def get(self, session_id: str) -> ClaimIntakeRecord | None:
        """Read one session consistently."""
        response = self._table.get_item(
            Key={"session_id": session_id},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            return None
        try:
            return ClaimIntakeRecord.model_validate(item)
        except ValidationError as error:
            raise RepositoryDataError(
                f"Invalid claim-intake state for session_id={session_id!r}"
            ) from error

    def save(self, record: ClaimIntakeRecord) -> None:
        """Write JSON-compatible state without unsupported float values."""
        item = json.loads(record.model_dump_json(), parse_float=Decimal)
        self._table.put_item(Item=item)
