"""Classification checks grounded in the supplied synthetic sample PDFs."""

from pathlib import Path

from pypdf import PdfReader

from app.models import DisputeDocumentType
from app.tools import classify_document_text


def test_supplied_onr_and_idr_samples_classify_deterministically() -> None:
    samples = {
        "synthetic_onr_case_001.pdf": DisputeDocumentType.ONR,
        "synthetic_idr_case_001.pdf": DisputeDocumentType.IDR,
    }

    for file_name, expected_type in samples.items():
        reader = PdfReader(Path("demo") / file_name)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

        assert classify_document_text(text) is expected_type


def test_ambiguous_text_remains_unknown() -> None:
    assert (
        classify_document_text("Open negotiation history and Federal IDR reference")
        is DisputeDocumentType.UNKNOWN
    )
