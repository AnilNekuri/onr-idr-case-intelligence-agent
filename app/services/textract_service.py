"""Amazon Textract orchestration for asynchronous multi-page PDF analysis."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)


class TextractAnalysisError(RuntimeError):
    """Raised when Textract cannot produce a usable analysis."""


@dataclass(frozen=True, slots=True)
class RawTextractResult:
    """Combined pages returned by the asynchronous Textract API."""

    job_id: str
    blocks: list[dict[str, Any]]
    document_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class TextractService:
    """Start, poll, and paginate a Textract document-analysis job."""

    def __init__(
        self,
        bucket_name: str,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        textract_client: Any | None = None,
        poll_interval_seconds: float = 2.0,
        max_polls: int = 300,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not bucket_name.strip():
            raise ValueError("bucket_name must not be empty")
        if poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds must not be negative")
        if max_polls < 1:
            raise ValueError("max_polls must be at least 1")

        if textract_client is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            textract_client = session.client("textract")

        self._bucket_name = bucket_name
        self._client = textract_client
        self._poll_interval_seconds = poll_interval_seconds
        self._max_polls = max_polls
        self._sleep = sleep

    def analyze_pdf(self, *, key: str) -> RawTextractResult:
        """Analyze one S3 PDF and return all result pages as a single block list."""
        if not key.strip():
            raise ValueError("key must not be empty")

        try:
            start = self._client.start_document_analysis(
                DocumentLocation={
                    "S3Object": {"Bucket": self._bucket_name, "Name": key}
                },
                FeatureTypes=["FORMS", "TABLES", "LAYOUT"],
            )
            job_id = str(start["JobId"])
        except (BotoCoreError, ClientError, KeyError, TypeError) as error:
            raise TextractAnalysisError(
                "Amazon Textract could not start document analysis"
            ) from error

        first_page = self._wait_for_completion(job_id)
        status = str(first_page.get("JobStatus", ""))
        warnings = self._status_warnings(first_page)
        if status == "PARTIAL_SUCCESS":
            warnings.insert(0, "Textract completed with partial success")

        blocks = self._blocks(first_page)
        metadata = dict(first_page.get("DocumentMetadata", {}))
        next_token = first_page.get("NextToken")
        while next_token:
            try:
                page = self._client.get_document_analysis(
                    JobId=job_id,
                    NextToken=str(next_token),
                    MaxResults=1000,
                )
            except (BotoCoreError, ClientError) as error:
                raise TextractAnalysisError(
                    "Amazon Textract result pagination failed"
                ) from error
            blocks.extend(self._blocks(page))
            warnings.extend(self._status_warnings(page))
            next_token = page.get("NextToken")

        return RawTextractResult(
            job_id=job_id,
            blocks=blocks,
            document_metadata=metadata,
            warnings=list(dict.fromkeys(warnings)),
        )

    def _wait_for_completion(self, job_id: str) -> dict[str, Any]:
        for poll_number in range(self._max_polls):
            try:
                response = self._client.get_document_analysis(
                    JobId=job_id,
                    MaxResults=1000,
                )
            except (BotoCoreError, ClientError) as error:
                raise TextractAnalysisError(
                    "Amazon Textract job polling failed"
                ) from error

            status = str(response.get("JobStatus", ""))
            if status in {"SUCCEEDED", "PARTIAL_SUCCESS"}:
                return dict(response)
            if status == "FAILED":
                message = str(response.get("StatusMessage", "unknown reason"))
                raise TextractAnalysisError(f"Textract analysis failed: {message}")
            if status != "IN_PROGRESS":
                raise TextractAnalysisError(
                    f"Textract returned unexpected job status: {status or 'missing'}"
                )
            if poll_number + 1 < self._max_polls:
                self._sleep(self._poll_interval_seconds)

        raise TextractAnalysisError(
            f"Textract analysis did not finish after {self._max_polls} polls"
        )

    @staticmethod
    def _blocks(response: dict[str, Any]) -> list[dict[str, Any]]:
        blocks = response.get("Blocks", [])
        if not isinstance(blocks, list):
            raise TextractAnalysisError("Textract returned an invalid Blocks value")
        return [block for block in blocks if isinstance(block, dict)]

    @staticmethod
    def _status_warnings(response: dict[str, Any]) -> list[str]:
        result: list[str] = []
        for warning in response.get("Warnings", []):
            if not isinstance(warning, dict):
                continue
            code = str(warning.get("ErrorCode", "Textract warning"))
            pages = warning.get("Pages", [])
            page_text = f" on pages {pages}" if pages else ""
            result.append(f"{code}{page_text}")
        return result
