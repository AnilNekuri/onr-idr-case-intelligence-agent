"""Validated domain models for ONR/IDR cases."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyString = Annotated[str, Field(min_length=1)]


class CaseType(StrEnum):
    """Supported negotiation and dispute-resolution case types."""

    ONR = "ONR"
    IDR = "IDR"


class CaseStatus(StrEnum):
    """Deterministic lifecycle states for a case."""

    NEW = "NEW"
    INCOMPLETE = "INCOMPLETE"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_PROVIDER_RESPONSE = "PENDING_PROVIDER_RESPONSE"
    COMPLETE = "COMPLETE"


class CaseEventType(StrEnum):
    """Supported authoritative timeline event types."""

    CASE_CREATED = "CASE_CREATED"
    NOTICE_SENT = "NOTICE_SENT"
    DOCUMENT_RECEIVED = "DOCUMENT_RECEIVED"
    PROVIDER_RESPONSE_RECEIVED = "PROVIDER_RESPONSE_RECEIVED"
    STATUS_CHANGED = "STATUS_CHANGED"
    CASE_COMPLETED = "CASE_COMPLETED"


class DomainModel(BaseModel):
    """Shared validation behavior for domain models."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Document(DomainModel):
    """Metadata that identifies a supporting case document."""

    document_id: NonEmptyString
    file_name: NonEmptyString
    s3_key: NonEmptyString


class CaseEvent(DomainModel):
    """An authoritative event in a case timeline."""

    date: date
    type: CaseEventType
    description: NonEmptyString


class Case(DomainModel):
    """The authoritative data record for one ONR or IDR case."""

    case_id: NonEmptyString
    case_type: CaseType
    status: CaseStatus
    created_date: date
    open_negotiation_start_date: date
    open_negotiation_end_date: date
    provider_name: NonEmptyString
    provider_response_received: bool = False
    missing_documents: list[NonEmptyString] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    events: list[CaseEvent] = Field(default_factory=list)
    additional_notes: str | None = None

    @model_validator(mode="after")
    def validate_negotiation_date_order(self) -> Self:
        """Reject a negotiation window whose end precedes its start."""
        if self.open_negotiation_end_date < self.open_negotiation_start_date:
            raise ValueError(
                "open_negotiation_end_date must be on or after "
                "open_negotiation_start_date"
            )
        return self
