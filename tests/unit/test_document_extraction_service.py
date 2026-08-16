"""End-to-end orchestration tests with AWS boundaries replaced by stubs."""

import json
from pathlib import Path
from typing import Any

from app.models import Document, ExtractedDisputeDocument
from app.services.document_extraction_service import DocumentExtractionService
from app.services.textract_service import RawTextractResult


class StubDocumentRepository:
    def __init__(self) -> None:
        self.upload: dict[str, Any] | None = None

    def upload_pdf(
        self,
        case_id: str,
        file_name: str,
        content: bytes,
        *,
        metadata: dict[str, str] | None = None,
        temporary: bool = False,
    ) -> Document:
        self.upload = {
            "case_id": case_id,
            "file_name": file_name,
            "content": content,
            "metadata": metadata,
            "temporary": temporary,
        }
        return Document(
            document_id="DOC-1",
            file_name=file_name,
            s3_key="temporary/EXTRACT/DOC-1/document.pdf",
        )

    def get(self, s3_key: str) -> bytes:
        raise NotImplementedError

    def get_metadata(self, s3_key: str) -> dict[str, str]:
        raise NotImplementedError


class StubTextractService:
    def __init__(self, result: RawTextractResult) -> None:
        self.result = result
        self.key: str | None = None

    def analyze_pdf(self, *, key: str) -> RawTextractResult:
        self.key = key
        return self.result


class StubBedrockService:
    def __init__(self, document: ExtractedDisputeDocument) -> None:
        self.document = document
        self.call: dict[str, Any] | None = None

    def extract_dispute_fields(self, **kwargs: Any) -> ExtractedDisputeDocument:
        self.call = kwargs
        return self.document


def test_hybrid_pipeline_returns_values_evidence_and_missing_fields() -> None:
    data = json.loads(
        Path("tests/fixtures/onr_bedrock_response.json").read_text(encoding="utf-8")
    )
    data["source_file_name"] = "synthetic_onr_case_001.pdf"
    document = ExtractedDisputeDocument.model_validate(data)
    raw = RawTextractResult(
        job_id="JOB-1",
        blocks=[
            _line("Open Negotiation Notice", 0.01),
            _line("Document Type ONR", 0.02),
            _line("Notice Date", 0.03),
            _line("07/15/2026", 0.04),
            _line("Claim Number", 0.05),
            _line("CLM-987654321", 0.06),
            *_key_value_blocks("claim", "Claim Number", "CLM-987654321"),
            *_key_value_blocks("notice", "Notice Date", "07/15/2026"),
        ],
    )
    repository = StubDocumentRepository()
    textract = StubTextractService(raw)
    bedrock = StubBedrockService(document)
    service = DocumentExtractionService(repository, textract, bedrock)  # type: ignore[arg-type]

    result = service.extract(
        file_name="synthetic_onr_case_001.pdf", content=b"%PDF-synthetic"
    )

    assert result.document.document_type.value == "ONR"
    assert result.field_evidence["claim_number"].page == 1
    assert result.field_evidence["claim_number"].confidence == 97.0
    assert result.field_evidence["notice_date"].value == "2026-07-15"
    assert "claim_number" not in result.missing_fields
    assert "provider_npi" not in result.missing_fields
    assert repository.upload is not None and repository.upload["temporary"] is True
    assert textract.key == "temporary/EXTRACT/DOC-1/document.pdf"
    assert bedrock.call is not None
    assert "--- PAGE 1 ---" in bedrock.call["textract_text"]


def test_classification_disagreement_is_not_silently_resolved() -> None:
    data = json.loads(
        Path("tests/fixtures/idr_bedrock_response.json").read_text(encoding="utf-8")
    )
    data["source_file_name"] = "conflict.pdf"
    document = ExtractedDisputeDocument.model_validate(data)
    raw = RawTextractResult(
        job_id="JOB-1",
        blocks=[
            _line("Open Negotiation Notice", 0.01),
            _line("SYNTHETIC TRAINING DOCUMENT - OPEN NEGOTIATION", 0.02),
            _line("Document Type ONR", 0.03),
        ],
    )
    service = DocumentExtractionService(
        StubDocumentRepository(),  # type: ignore[arg-type]
        StubTextractService(raw),  # type: ignore[arg-type]
        StubBedrockService(document),  # type: ignore[arg-type]
    )

    result = service.extract(file_name="conflict.pdf", content=b"%PDF-synthetic")

    assert result.document.document_type.value == "UNKNOWN"
    assert any("classifications disagree" in warning for warning in result.warnings)


def _line(text: str, top: float) -> dict[str, Any]:
    return {
        "Id": f"line-{top}",
        "BlockType": "LINE",
        "Text": text,
        "Page": 1,
        "Confidence": 99.0,
        "Geometry": {"BoundingBox": {"Top": top, "Left": 0.1}},
    }


def _key_value_blocks(prefix: str, key: str, value: str) -> list[dict[str, Any]]:
    return [
        {"Id": f"{prefix}-key-word", "BlockType": "WORD", "Text": key, "Page": 1},
        {
            "Id": f"{prefix}-value-word",
            "BlockType": "WORD",
            "Text": value,
            "Page": 1,
        },
        {
            "Id": f"{prefix}-key",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["KEY"],
            "Page": 1,
            "Confidence": 98.0,
            "Relationships": [
                {"Type": "CHILD", "Ids": [f"{prefix}-key-word"]},
                {"Type": "VALUE", "Ids": [f"{prefix}-value"]},
            ],
        },
        {
            "Id": f"{prefix}-value",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["VALUE"],
            "Page": 1,
            "Confidence": 97.0,
            "Relationships": [
                {"Type": "CHILD", "Ids": [f"{prefix}-value-word"]}
            ],
        },
    ]
