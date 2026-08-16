"""Validated models for ONR/IDR document extraction and OCR evidence."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonNegativeAmount = Annotated[Decimal, Field(ge=0)]


class ExtractionModel(BaseModel):
    """Shared strict validation behavior for extraction data."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class DisputeDocumentType(StrEnum):
    """Document classes supported by the extraction workflow."""

    ONR = "ONR"
    IDR = "IDR"
    UNKNOWN = "UNKNOWN"


class ExtractionSource(StrEnum):
    """System responsible for an extracted or normalized value."""

    TEXTRACT = "TEXTRACT"
    BEDROCK = "BEDROCK"
    HYBRID = "HYBRID"


class FieldEvidence(ExtractionModel):
    """OCR evidence supporting one normalized field value."""

    value: str | None = None
    source: ExtractionSource
    page: int | None = Field(default=None, ge=1)
    confidence: float | None = Field(default=None, ge=0, le=100)
    raw_text: str | None = None


class ExtractedDisputeDocument(ExtractionModel):
    """Stable JSON contract shared by ONR and IDR documents.

    Fields that do not apply to a particular document type remain ``None``. This
    lets downstream consumers use one contract without losing type-specific data.
    """

    document_type: DisputeDocumentType
    source_file_name: str

    claim_number: str | None = None
    provider_claim_number: str | None = None
    member_id: str | None = None

    provider_name: str | None = None
    provider_npi: str | None = None
    provider_tin: str | None = None

    date_of_service: date | None = None
    cpt_hcpcs: list[str] = Field(default_factory=list)

    billed_amount: NonNegativeAmount | None = None
    initial_payment: NonNegativeAmount | None = None
    initial_payment_or_denial_date: date | None = None
    qpa: NonNegativeAmount | None = None
    requested_amount: NonNegativeAmount | None = None
    payer_offer: NonNegativeAmount | None = None

    notice_date: date | None = None
    open_negotiation_start_date: date | None = None
    open_negotiation_end_date: date | None = None
    idr_initiation_date: date | None = None

    federal_idr_reference: str | None = None
    initiating_party: str | None = None
    negotiation_outcome: str | None = None
    extraction_summary: str | None = None


class TextractLine(ExtractionModel):
    """One OCR line with its page and confidence."""

    text: str
    page: int = Field(ge=1)
    confidence: float | None = Field(default=None, ge=0, le=100)


class TextractKeyValue(ExtractionModel):
    """One normalized Textract form key/value pair."""

    key: str
    value: str
    page: int = Field(ge=1)
    confidence: float | None = Field(default=None, ge=0, le=100)


class TextractTable(ExtractionModel):
    """A compact row-oriented representation of one Textract table."""

    page: int = Field(ge=1)
    rows: list[list[str]] = Field(default_factory=list)


class TextractPage(ExtractionModel):
    """Normalized content belonging to one PDF page."""

    page: int = Field(ge=1)
    lines: list[TextractLine] = Field(default_factory=list)
    key_values: list[TextractKeyValue] = Field(default_factory=list)
    tables: list[TextractTable] = Field(default_factory=list)


class NormalizedTextractDocument(ExtractionModel):
    """LLM-ready Textract content with layout evidence retained separately."""

    job_id: str | None = None
    full_text: str
    pages: list[TextractPage] = Field(default_factory=list)
    key_values: list[TextractKeyValue] = Field(default_factory=list)
    tables: list[TextractTable] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DisputeDocumentExtraction(ExtractionModel):
    """Final validated extraction plus traceable OCR evidence."""

    document: ExtractedDisputeDocument
    field_evidence: dict[str, FieldEvidence] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extraction_mode: ExtractionSource
    raw_textract_text: str | None = None
