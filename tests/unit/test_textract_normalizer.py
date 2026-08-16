"""Tests for form, table, and page normalization from Textract blocks."""

from app.services.textract_normalizer import normalize_textract
from app.services.textract_service import RawTextractResult


def test_normalizes_reading_order_form_evidence_and_table_rows() -> None:
    blocks = [
        _line("line-2", "CLM-987654321", top=0.2),
        _line("line-1", "Claim Number", top=0.1),
        _word("key-word", "Claim Number"),
        _word("value-word", "CLM-987654321"),
        {
            "Id": "key",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["KEY"],
            "Page": 1,
            "Confidence": 98.0,
            "Relationships": [
                {"Type": "CHILD", "Ids": ["key-word"]},
                {"Type": "VALUE", "Ids": ["value"]},
            ],
        },
        {
            "Id": "value",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["VALUE"],
            "Page": 1,
            "Confidence": 97.0,
            "Relationships": [{"Type": "CHILD", "Ids": ["value-word"]}],
        },
        {
            "Id": "table",
            "BlockType": "TABLE",
            "Page": 1,
            "Relationships": [{"Type": "CHILD", "Ids": ["cell"]}],
        },
        {
            "Id": "cell",
            "BlockType": "CELL",
            "Page": 1,
            "RowIndex": 1,
            "ColumnIndex": 1,
            "Relationships": [{"Type": "CHILD", "Ids": ["value-word"]}],
        },
    ]

    normalized = normalize_textract(
        RawTextractResult(job_id="JOB-1", blocks=blocks)
    )

    assert normalized.full_text == "--- PAGE 1 ---\nClaim Number\nCLM-987654321"
    assert normalized.key_values[0].model_dump() == {
        "key": "Claim Number",
        "value": "CLM-987654321",
        "page": 1,
        "confidence": 97.0,
    }
    assert normalized.tables[0].rows == [["CLM-987654321"]]


def _line(block_id: str, text: str, *, top: float) -> dict[str, object]:
    return {
        "Id": block_id,
        "BlockType": "LINE",
        "Text": text,
        "Page": 1,
        "Confidence": 99.0,
        "Geometry": {"BoundingBox": {"Top": top, "Left": 0.1}},
    }


def _word(block_id: str, text: str) -> dict[str, object]:
    return {"Id": block_id, "BlockType": "WORD", "Text": text, "Page": 1}
