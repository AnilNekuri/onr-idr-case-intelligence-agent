"""Validated contracts for conversational claim intake."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.document_extraction import (
    DisputeDocumentExtraction,
    DisputeDocumentType,
)


class ClaimIntakeModel(BaseModel):
    """Shared strict validation for claim-intake messages and state."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ClaimIntakeAction(StrEnum):
    """Explicit events accepted by the conversational runtime."""

    START = "START"
    MESSAGE = "MESSAGE"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    CONFIRM_SUBMISSION = "CONFIRM_SUBMISSION"
    GET_SUMMARY = "GET_SUMMARY"
    CANCEL = "CANCEL"


class ClaimIntakeStage(StrEnum):
    """Durable conversational workflow stages."""

    WELCOME = "WELCOME"
    AWAITING_DOCUMENT = "AWAITING_DOCUMENT"
    REVIEW_AND_CONFIRM = "REVIEW_AND_CONFIRM"
    SUBMITTED = "SUBMITTED"


class ClaimExpectedInput(StrEnum):
    """Hint used by presentation clients to render the next control."""

    MESSAGE = "MESSAGE"
    PDF = "PDF"
    SUBMISSION_CONFIRMATION = "SUBMISSION_CONFIRMATION"
    NONE = "NONE"


class StoredIntakeDocument(ClaimIntakeModel):
    """Reference to a PDF already stored in the configured private bucket."""

    document_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    s3_key: str = Field(min_length=1)


class ClaimIntakeCitation(ClaimIntakeModel):
    """Knowledge Base source attached to next-step guidance."""

    source_id: str
    document_location: str


class ClaimIntakeRequest(ClaimIntakeModel):
    """One invocation sent to the claim-intake AgentCore runtime."""

    action: ClaimIntakeAction
    message: str | None = None
    document: StoredIntakeDocument | None = None
    confirmation: bool | None = None
    idempotency_key: str | None = None


class ClaimIntakeRecord(ClaimIntakeModel):
    """Durable state for one conversational intake session."""

    session_id: str = Field(min_length=33)
    stage: ClaimIntakeStage = ClaimIntakeStage.WELCOME
    document: StoredIntakeDocument | None = None
    extraction: DisputeDocumentExtraction | None = None
    document_summary: str | None = None
    case_id: str | None = None
    duplicate_detected: bool = False
    submission_idempotency_key: str | None = None
    final_summary: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    citations: list[ClaimIntakeCitation] = Field(default_factory=list)
    updated_at: datetime
    expires_at: int = Field(gt=0)


class ClaimIntakeResponse(ClaimIntakeModel):
    """Structured response returned to any chat presentation client."""

    session_id: str
    state: ClaimIntakeStage
    message: str
    expected_input: ClaimExpectedInput
    document_type: DisputeDocumentType | None = None
    summary: str | None = None
    extracted_fields: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    can_submit: bool = False
    case_id: str | None = None
    duplicate_detected: bool = False
    next_actions: list[str] = Field(default_factory=list)
    citations: list[ClaimIntakeCitation] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
