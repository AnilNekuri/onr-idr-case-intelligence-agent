"""Unit tests for asynchronous Textract polling and result pagination."""

from typing import Any

import pytest

from app.services.textract_service import TextractAnalysisError, TextractService


class FakeTextractClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.start_request: dict[str, Any] | None = None
        self.get_requests: list[dict[str, Any]] = []

    def start_document_analysis(self, **kwargs: Any) -> dict[str, str]:
        self.start_request = kwargs
        return {"JobId": "JOB-1001"}

    def get_document_analysis(self, **kwargs: Any) -> dict[str, Any]:
        self.get_requests.append(kwargs)
        return self.responses.pop(0)


def test_analyze_pdf_polls_and_combines_paginated_blocks() -> None:
    client = FakeTextractClient(
        [
            {"JobStatus": "IN_PROGRESS"},
            {
                "JobStatus": "SUCCEEDED",
                "Blocks": [{"Id": "1"}],
                "NextToken": "NEXT",
                "DocumentMetadata": {"Pages": 2},
            },
            {"JobStatus": "SUCCEEDED", "Blocks": [{"Id": "2"}]},
        ]
    )
    sleeps: list[float] = []
    service = TextractService(
        "synthetic-bucket",
        textract_client=client,
        poll_interval_seconds=0.25,
        sleep=sleeps.append,
    )

    result = service.analyze_pdf(key="temporary/doc.pdf")

    assert result.job_id == "JOB-1001"
    assert [block["Id"] for block in result.blocks] == ["1", "2"]
    assert result.document_metadata == {"Pages": 2}
    assert sleeps == [0.25]
    assert client.start_request == {
        "DocumentLocation": {
            "S3Object": {
                "Bucket": "synthetic-bucket",
                "Name": "temporary/doc.pdf",
            }
        },
        "FeatureTypes": ["FORMS", "TABLES", "LAYOUT"],
    }
    assert client.get_requests[-1]["NextToken"] == "NEXT"


def test_failed_job_raises_clear_error() -> None:
    client = FakeTextractClient(
        [{"JobStatus": "FAILED", "StatusMessage": "unsupported document"}]
    )
    service = TextractService("synthetic-bucket", textract_client=client)

    with pytest.raises(TextractAnalysisError, match="unsupported document"):
        service.analyze_pdf(key="temporary/doc.pdf")
