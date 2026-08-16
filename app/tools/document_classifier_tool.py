"""Deterministic high-confidence classification signals for ONR/IDR text."""

import re

from app.models.document_extraction import DisputeDocumentType

_IDR_SIGNALS = (
    r"federal independent dispute resolution",
    r"synthetic training document\s*-\s*federal idr",
    r"document type\s+idr\b",
    r"idr initiation date",
)
_ONR_SIGNALS = (
    r"open negotiation notice",
    r"synthetic training document\s*-\s*open negotiation",
    r"document type\s+onr\b",
    r"notice date",
)


def classify_document_text(text: str) -> DisputeDocumentType:
    """Classify only when one document family has stronger explicit signals."""
    normalized = " ".join(text.lower().split())
    idr_score = sum(bool(re.search(signal, normalized)) for signal in _IDR_SIGNALS)
    onr_score = sum(bool(re.search(signal, normalized)) for signal in _ONR_SIGNALS)
    if idr_score > onr_score and idr_score >= 2:
        return DisputeDocumentType.IDR
    if onr_score > idr_score and onr_score >= 2:
        return DisputeDocumentType.ONR
    return DisputeDocumentType.UNKNOWN
