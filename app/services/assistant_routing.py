"""Deterministic routing and copy for the conversational assistant."""

import re
from enum import StrEnum

from app.models import DisputeDocumentExtraction, DisputeDocumentType


class AssistantRoute(StrEnum):
    """Supported conversational entry points."""

    GENERAL_QUESTION = "GENERAL_QUESTION"
    CLAIM_INTAKE = "CLAIM_INTAKE"


_CLAIM_NOUN = re.compile(r"\b(?:claim|dispute|case|onr|idr)\b", re.IGNORECASE)
_CLAIM_ACTION = re.compile(
    r"\b(?:process|submit|start|open|file|upload|review|handle|initiate)\w*\b",
    re.IGNORECASE,
)
_DIRECT_PATTERNS = (
    re.compile(r"\bi\s+(?:have|need|want)\s+(?:an?\s+)?(?:claim|dispute)\b", re.I),
    re.compile(r"\bprocess\s+(?:an?\s+|my\s+)?claim\b", re.I),
)


def route_assistant_message(message: str) -> AssistantRoute:
    """Route explicit claim-processing requests; all other text goes to RAG."""
    normalized = " ".join(message.split())
    if any(pattern.search(normalized) for pattern in _DIRECT_PATTERNS):
        return AssistantRoute.CLAIM_INTAKE
    if _CLAIM_NOUN.search(normalized) and _CLAIM_ACTION.search(normalized):
        return AssistantRoute.CLAIM_INTAKE
    return AssistantRoute.GENERAL_QUESTION


def build_extraction_message(result: DisputeDocumentExtraction) -> str:
    """Build the deterministic workflow handoff after PDF classification."""
    document_type = result.document.document_type
    if document_type is DisputeDocumentType.UNKNOWN:
        return (
            "I couldn't identify this PDF as an ONR or IDR document, so I can't "
            "continue the claim workflow. Please upload a supported ONR or IDR PDF."
        )

    missing = result.missing_fields
    if missing:
        review = ", ".join(field.replace("_", " ") for field in missing)
        readiness = f"Before continuing, review these missing fields: {review}."
    else:
        readiness = "All workflow review fields were extracted."

    if document_type is DisputeDocumentType.ONR:
        next_step = (
            "This follows the open-negotiation workflow:\n\n"
            "1. Verify the notice fields and counterparty contact.\n"
            "2. Preserve proof that the notice was sent and received.\n"
            "3. Track the full open-negotiation period with deterministic dates.\n"
            "4. If no agreement is reached, assess the IDR initiation window."
        )
    else:
        next_step = (
            "This follows the Federal IDR workflow:\n\n"
            "1. Verify that the full open-negotiation period ended without agreement.\n"
            "2. Confirm the IDR initiation record, reference, and other-party notice.\n"
            "3. Track entity selection, offers, fees, and determination milestones.\n"
            "4. Record any settlement, determination, and required payment."
        )
    return f"I identified this as **{document_type.value}**. {readiness} {next_step}"
