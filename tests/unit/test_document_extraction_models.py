"""Validation tests for the stable ONR/IDR extraction contract."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import ExtractedDisputeDocument

FIXTURES = Path("tests/fixtures")


@pytest.mark.parametrize(
    ("fixture_name", "document_type", "requested_amount", "payer_offer"),
    [
        ("onr_bedrock_response.json", "ONR", Decimal("6000"), None),
        ("idr_bedrock_response.json", "IDR", Decimal("5200"), Decimal("3000")),
    ],
)
def test_onr_and_idr_share_one_validated_contract(
    fixture_name: str,
    document_type: str,
    requested_amount: Decimal,
    payer_offer: Decimal | None,
) -> None:
    data = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    data["source_file_name"] = fixture_name.replace("bedrock_response.json", "case.pdf")

    document = ExtractedDisputeDocument.model_validate(data)

    assert document.document_type.value == document_type
    assert document.requested_amount == requested_amount
    assert document.payer_offer == payer_offer
    assert set(document.model_dump(mode="json")) == set(
        ExtractedDisputeDocument.model_fields
    )


def test_negative_amount_is_rejected() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        ExtractedDisputeDocument(
            document_type="ONR",
            source_file_name="synthetic.pdf",
            billed_amount=Decimal("-1"),
        )


def test_unexpected_model_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExtractedDisputeDocument.model_validate(
            {
                "document_type": "ONR",
                "source_file_name": "synthetic.pdf",
                "claim_is_valid": True,
            }
        )
