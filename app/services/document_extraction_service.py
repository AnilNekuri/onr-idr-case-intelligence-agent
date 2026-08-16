"""End-to-end S3, Textract, Bedrock, validation, and evidence workflow."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import uuid4

from app.models.document_extraction import (
    DisputeDocumentExtraction,
    DisputeDocumentType,
    ExtractedDisputeDocument,
    ExtractionSource,
    FieldEvidence,
    NormalizedTextractDocument,
    TextractLine,
)
from app.repositories import DocumentRepository
from app.services.bedrock_extraction_service import DisputeFieldExtractor
from app.services.textract_normalizer import normalize_textract
from app.services.textract_service import TextractService
from app.tools.document_classifier_tool import classify_document_text

_COMMON_REVIEW_FIELDS = (
    "claim_number",
    "provider_name",
    "provider_npi",
    "date_of_service",
    "cpt_hcpcs",
    "billed_amount",
    "initial_payment",
    "initial_payment_or_denial_date",
    "qpa",
    "requested_amount",
    "open_negotiation_start_date",
    "open_negotiation_end_date",
)
_TYPE_REVIEW_FIELDS = {
    DisputeDocumentType.ONR: ("notice_date", "initiating_party"),
    DisputeDocumentType.IDR: (
        "federal_idr_reference",
        "idr_initiation_date",
        "initiating_party",
        "payer_offer",
        "negotiation_outcome",
    ),
}
_FIELD_LABELS = {
    "document_type": ("document type",),
    "claim_number": ("claim number",),
    "provider_claim_number": ("provider claim number",),
    "member_id": ("member id",),
    "provider_name": ("provider name",),
    "provider_npi": ("provider npi", "npi"),
    "provider_tin": ("provider tin", "tin"),
    "date_of_service": ("date of service",),
    "cpt_hcpcs": ("cpt/hcpcs", "cpt", "hcpcs"),
    "billed_amount": ("billed amount",),
    "initial_payment": ("initial payment",),
    "initial_payment_or_denial_date": (
        "initial payment date",
        "denial date",
        "notice of denial date",
    ),
    "qpa": ("qualifying payment amount", "qpa"),
    "requested_amount": ("requested amount", "provider offer"),
    "payer_offer": ("payer offer",),
    "notice_date": ("notice date",),
    "open_negotiation_start_date": ("open negotiation start date",),
    "open_negotiation_end_date": ("open negotiation end date",),
    "idr_initiation_date": ("idr initiation date",),
    "federal_idr_reference": ("federal idr reference", "idr reference"),
    "initiating_party": ("initiating party",),
    "negotiation_outcome": ("negotiation outcome",),
}


class DocumentExtractionService:
    """Coordinate the auditable hybrid document-extraction pipeline."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        textract_service: TextractService,
        bedrock_service: DisputeFieldExtractor,
    ) -> None:
        self._document_repository = document_repository
        self._textract_service = textract_service
        self._bedrock_service = bedrock_service

    def extract(
        self, *, file_name: str, content: bytes
    ) -> DisputeDocumentExtraction:
        """Store and extract one PDF into the stable ONR/IDR JSON contract."""
        intake_id = f"EXTRACT-{uuid4().hex}"
        stored = self._document_repository.upload_pdf(
            intake_id,
            file_name,
            content,
            metadata={"purpose": "document-extraction"},
            temporary=True,
        )
        return self.extract_stored(file_name=file_name, s3_key=stored.s3_key)

    def extract_stored(
        self,
        *,
        file_name: str,
        s3_key: str,
    ) -> DisputeDocumentExtraction:
        """Extract a PDF already stored in the configured private S3 bucket."""
        if not file_name.strip():
            raise ValueError("file_name must not be empty")
        if not s3_key.strip():
            raise ValueError("s3_key must not be empty")
        raw = self._textract_service.analyze_pdf(key=s3_key)
        normalized = normalize_textract(raw)
        document = self._bedrock_service.extract_dispute_fields(
            file_name=file_name,
            textract_text=normalized.full_text,
            key_values=normalized.key_values,
        )

        warnings = list(normalized.warnings)
        deterministic_type = classify_document_text(normalized.full_text)
        if (
            deterministic_type is DisputeDocumentType.UNKNOWN
            and document.document_type is not DisputeDocumentType.UNKNOWN
        ):
            warnings.append(
                "Deterministic classification could not confirm an ONR or IDR "
                "document; document_type was set to UNKNOWN"
            )
            document = document.model_copy(
                update={"document_type": DisputeDocumentType.UNKNOWN}
            )
        elif document.document_type is not deterministic_type:
            warnings.append(
                "Deterministic and Bedrock document classifications disagree; "
                "document_type was set to UNKNOWN for analyst review"
            )
            document = document.model_copy(
                update={"document_type": DisputeDocumentType.UNKNOWN}
            )

        evidence, evidence_warnings = _build_field_evidence(document, normalized)
        warnings.extend(evidence_warnings)
        return DisputeDocumentExtraction(
            document=document,
            field_evidence=evidence,
            missing_fields=_find_missing_fields(document),
            warnings=list(dict.fromkeys(warnings)),
            extraction_mode=ExtractionSource.HYBRID,
            raw_textract_text=normalized.full_text,
        )


def _find_missing_fields(document: ExtractedDisputeDocument) -> list[str]:
    fields = list(_COMMON_REVIEW_FIELDS)
    fields.extend(_TYPE_REVIEW_FIELDS.get(document.document_type, ()))
    return [field for field in fields if not getattr(document, field)]


def _build_field_evidence(
    document: ExtractedDisputeDocument,
    normalized: NormalizedTextractDocument,
) -> tuple[dict[str, FieldEvidence], list[str]]:
    evidence: dict[str, FieldEvidence] = {}
    warnings: list[str] = []
    values = document.model_dump(exclude_none=True)
    for field_name, value in values.items():
        if field_name in {"source_file_name", "extraction_summary"} or value == []:
            continue
        matched = _best_evidence(field_name, value, normalized)
        if matched is None:
            warnings.append(f"No direct Textract evidence found for {field_name}")
            continue
        raw_text, page, confidence = matched
        evidence[field_name] = FieldEvidence(
            value=_display_value(value),
            source=ExtractionSource.HYBRID,
            page=page,
            confidence=confidence,
            raw_text=raw_text,
        )
    return evidence, warnings


def _best_evidence(
    field_name: str,
    value: Any,
    normalized: NormalizedTextractDocument,
) -> tuple[str, int, float | None] | None:
    labels = _FIELD_LABELS.get(field_name, ())
    pairs = sorted(
        normalized.key_values,
        key=lambda pair: (
            not any(label in pair.key.casefold() for label in labels),
            -(pair.confidence or -1),
        ),
    )
    for pair in pairs:
        if _values_match(field_name, value, pair.value):
            return f"{pair.key}: {pair.value}", pair.page, pair.confidence

    for page in normalized.pages:
        for line in page.lines:
            if _line_supports(field_name, value, line):
                return line.text, line.page, line.confidence
    return None


def _values_match(field_name: str, expected: Any, observed: str) -> bool:
    expected_values = expected if isinstance(expected, list) else [expected]
    return any(
        _normalized_value(field_name, item) == _normalized_value(field_name, observed)
        for item in expected_values
    )


def _line_supports(field_name: str, expected: Any, line: TextractLine) -> bool:
    expected_values = expected if isinstance(expected, list) else [expected]
    line_text = line.text.casefold()
    return any(
        variant.casefold() in line_text
        for item in expected_values
        for variant in _display_variants(item)
        if variant
    )


def _normalized_value(field_name: str, value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if field_name in {
        "billed_amount",
        "initial_payment",
        "qpa",
        "requested_amount",
        "payer_offer",
    }:
        try:
            return str(Decimal(re.sub(r"[^0-9.-]", "", str(value))))
        except InvalidOperation:
            return str(value).strip().casefold()
    if field_name.endswith("_date") or field_name == "date_of_service":
        if isinstance(value, date):
            return value.isoformat()
        for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(str(value).strip(), pattern).date().isoformat()
            except ValueError:
                pass
    return " ".join(str(value).strip().casefold().split())


def _display_variants(value: Any) -> set[str]:
    if isinstance(value, Enum):
        return {str(value.value)}
    if isinstance(value, date):
        return {value.isoformat(), value.strftime("%m/%d/%Y")}
    if isinstance(value, Decimal):
        return {str(value), f"{value:.2f}", f"${value:,.2f}"}
    return {str(value)}


def _display_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
