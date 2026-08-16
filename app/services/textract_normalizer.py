"""Normalize Amazon Textract's block graph into compact, ordered evidence."""

from collections import defaultdict
from typing import Any

from app.models.document_extraction import (
    NormalizedTextractDocument,
    TextractKeyValue,
    TextractLine,
    TextractPage,
    TextractTable,
)
from app.services.textract_service import RawTextractResult


def normalize_textract(result: RawTextractResult) -> NormalizedTextractDocument:
    """Convert raw Textract blocks to page text, form pairs, and table rows."""
    by_id = {
        str(block["Id"]): block
        for block in result.blocks
        if isinstance(block.get("Id"), str)
    }
    lines_by_page: dict[int, list[tuple[float, float, TextractLine]]] = defaultdict(
        list
    )
    key_values_by_page: dict[int, list[TextractKeyValue]] = defaultdict(list)
    tables_by_page: dict[int, list[TextractTable]] = defaultdict(list)
    observed_pages: set[int] = set()

    for block in result.blocks:
        page = _page_number(block)
        observed_pages.add(page)
        block_type = block.get("BlockType")
        if block_type == "LINE":
            text = str(block.get("Text", "")).strip()
            if text:
                top, left = _position(block)
                lines_by_page[page].append(
                    (
                        top,
                        left,
                        TextractLine(
                            text=text,
                            page=page,
                            confidence=_confidence(block),
                        ),
                    )
                )
        elif block_type == "KEY_VALUE_SET" and "KEY" in block.get(
            "EntityTypes", []
        ):
            key = _relationship_text(block, "CHILD", by_id)
            value_blocks = _relationship_blocks(block, "VALUE", by_id)
            value = " ".join(
                part
                for value_block in value_blocks
                if (part := _relationship_text(value_block, "CHILD", by_id))
            ).strip()
            if key:
                confidence_values = [
                    item
                    for item in (
                        _confidence(block),
                        *(_confidence(value_block) for value_block in value_blocks),
                    )
                    if item is not None
                ]
                key_values_by_page[page].append(
                    TextractKeyValue(
                        key=key,
                        value=value,
                        page=page,
                        confidence=(
                            min(confidence_values) if confidence_values else None
                        ),
                    )
                )
        elif block_type == "TABLE":
            rows = _table_rows(block, by_id)
            tables_by_page[page].append(TextractTable(page=page, rows=rows))

    pages: list[TextractPage] = []
    full_text_pages: list[str] = []
    for page_number in sorted(observed_pages):
        ordered_lines = [
            line
            for _, _, line in sorted(
                lines_by_page[page_number], key=lambda item: (item[0], item[1])
            )
        ]
        page_model = TextractPage(
            page=page_number,
            lines=ordered_lines,
            key_values=key_values_by_page[page_number],
            tables=tables_by_page[page_number],
        )
        pages.append(page_model)
        text = "\n".join(line.text for line in ordered_lines)
        full_text_pages.append(f"--- PAGE {page_number} ---\n{text}".rstrip())

    key_values = [pair for page in pages for pair in page.key_values]
    tables = [table for page in pages for table in page.tables]
    return NormalizedTextractDocument(
        job_id=result.job_id,
        full_text="\n\n".join(full_text_pages),
        pages=pages,
        key_values=key_values,
        tables=tables,
        warnings=result.warnings,
    )


def _page_number(block: dict[str, Any]) -> int:
    page = block.get("Page", 1)
    return page if isinstance(page, int) and page >= 1 else 1


def _confidence(block: dict[str, Any]) -> float | None:
    value = block.get("Confidence")
    return float(value) if isinstance(value, int | float) else None


def _position(block: dict[str, Any]) -> tuple[float, float]:
    box = block.get("Geometry", {}).get("BoundingBox", {})
    top = box.get("Top", 0.0)
    left = box.get("Left", 0.0)
    return float(top), float(left)


def _relationship_blocks(
    block: dict[str, Any],
    relationship_type: str,
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    for relationship in block.get("Relationships", []):
        if relationship.get("Type") != relationship_type:
            continue
        for block_id in relationship.get("Ids", []):
            child = by_id.get(str(block_id))
            if child is not None:
                related.append(child)
    return related


def _relationship_text(
    block: dict[str, Any],
    relationship_type: str,
    by_id: dict[str, dict[str, Any]],
) -> str:
    parts: list[str] = []
    for child in _relationship_blocks(block, relationship_type, by_id):
        if child.get("BlockType") == "WORD":
            text = str(child.get("Text", "")).strip()
            if text:
                parts.append(text)
        elif child.get("BlockType") == "SELECTION_ELEMENT" and child.get(
            "SelectionStatus"
        ) == "SELECTED":
            parts.append("SELECTED")
    return " ".join(parts)


def _table_rows(
    table: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[list[str]]:
    cells: dict[tuple[int, int], str] = {}
    max_row = 0
    max_column = 0
    for cell in _relationship_blocks(table, "CHILD", by_id):
        if cell.get("BlockType") != "CELL":
            continue
        row = int(cell.get("RowIndex", 0))
        column = int(cell.get("ColumnIndex", 0))
        if row < 1 or column < 1:
            continue
        cells[(row, column)] = _relationship_text(cell, "CHILD", by_id)
        max_row = max(max_row, row)
        max_column = max(max_column, column)
    return [
        [cells.get((row, column), "") for column in range(1, max_column + 1)]
        for row in range(1, max_row + 1)
    ]
