"""DynamoDB implementation of the authoritative case repository contract."""

from typing import Any

import boto3  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.models import Case
from app.repositories.case_repository import RepositoryDataError


class DynamoDbCaseRepository:
    """Store each case as one DynamoDB item keyed by ``case_id``."""

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

    def get(self, case_id: str) -> Case | None:
        """Return one strongly consistent case, or ``None`` when absent."""
        response = self._table.get_item(
            Key={"case_id": case_id},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            return None

        try:
            return Case.model_validate(item)
        except ValidationError as error:
            raise RepositoryDataError(
                f"Invalid case data in DynamoDB table for case_id={case_id!r}"
            ) from error

    def save(self, case: Case) -> None:
        """Create or fully replace the item with the same case ID."""
        self._table.put_item(Item=case.model_dump(mode="json"))
