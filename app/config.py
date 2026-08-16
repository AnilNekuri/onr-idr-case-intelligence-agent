"""Environment-based application configuration."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when application configuration is missing or invalid."""


class CaseRepositoryKind(StrEnum):
    """Supported authoritative case repository implementations."""

    JSON = "json"
    DYNAMODB = "dynamodb"


class BedrockExtractionApi(StrEnum):
    """Bedrock endpoint used for semantic document extraction."""

    MANTLE = "mantle"
    RUNTIME = "runtime"


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    """Configuration needed to assemble repositories at the application edge."""

    case_repository: CaseRepositoryKind
    json_cases_path: Path
    aws_region: str
    aws_profile: str | None
    dynamodb_case_table: str | None
    s3_case_documents_bucket: str | None
    bedrock_model_id: str | None = None
    bedrock_extraction_model_id: str | None = None
    bedrock_extraction_api: BedrockExtractionApi = BedrockExtractionApi.MANTLE
    bedrock_knowledge_base_id: str | None = None
    agentcore_runtime_arn: str | None = None
    agentcore_endpoint_name: str | None = None
    claim_intake_table: str | None = None
    claim_agentcore_runtime_arn: str | None = None
    claim_agentcore_endpoint_name: str | None = None

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ApplicationSettings":
        """Read settings from an explicit mapping or the process environment."""
        values = os.environ if environment is None else environment
        raw_repository = values.get("CASE_REPOSITORY", "json").strip().lower()
        try:
            repository = CaseRepositoryKind(raw_repository)
        except ValueError as error:
            supported = ", ".join(item.value for item in CaseRepositoryKind)
            raise ConfigurationError(
                f"CASE_REPOSITORY must be one of: {supported}"
            ) from error
        raw_extraction_api = values.get(
            "BEDROCK_EXTRACTION_API", "mantle"
        ).strip().lower()
        try:
            extraction_api = BedrockExtractionApi(raw_extraction_api)
        except ValueError as error:
            supported = ", ".join(item.value for item in BedrockExtractionApi)
            raise ConfigurationError(
                f"BEDROCK_EXTRACTION_API must be one of: {supported}"
            ) from error

        settings = cls(
            case_repository=repository,
            json_cases_path=Path(values.get("JSON_CASES_PATH", "data/cases.json")),
            aws_region=values.get("AWS_REGION", "us-east-1"),
            aws_profile=cls._optional(values.get("AWS_PROFILE")),
            dynamodb_case_table=cls._optional(values.get("DYNAMODB_CASE_TABLE")),
            s3_case_documents_bucket=cls._optional(
                values.get("S3_CASE_DOCUMENTS_BUCKET")
            ),
            bedrock_model_id=cls._optional(values.get("BEDROCK_MODEL_ID")),
            bedrock_extraction_model_id=cls._optional(
                values.get("BEDROCK_EXTRACTION_MODEL_ID")
            ),
            bedrock_extraction_api=extraction_api,
            bedrock_knowledge_base_id=cls._optional(
                values.get("BEDROCK_KNOWLEDGE_BASE_ID")
            ),
            agentcore_runtime_arn=cls._optional(values.get("AGENTCORE_RUNTIME_ARN")),
            agentcore_endpoint_name=cls._optional(
                values.get("AGENTCORE_ENDPOINT_NAME")
            ),
            claim_intake_table=cls._optional(values.get("CLAIM_INTAKE_TABLE")),
            claim_agentcore_runtime_arn=cls._optional(
                values.get("CLAIM_AGENTCORE_RUNTIME_ARN")
            ),
            claim_agentcore_endpoint_name=cls._optional(
                values.get("CLAIM_AGENTCORE_ENDPOINT_NAME")
            ),
        )
        settings._validate()
        return settings

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _validate(self) -> None:
        if (
            self.case_repository is CaseRepositoryKind.DYNAMODB
            and self.dynamodb_case_table is None
        ):
            raise ConfigurationError(
                "DYNAMODB_CASE_TABLE is required when CASE_REPOSITORY=dynamodb"
            )
        if not self.aws_region.strip():
            raise ConfigurationError("AWS_REGION must not be empty")
        if (
            self.bedrock_knowledge_base_id is not None
            and re.fullmatch(r"[0-9A-Za-z]{10}", self.bedrock_knowledge_base_id) is None
        ):
            raise ConfigurationError(
                "BEDROCK_KNOWLEDGE_BASE_ID must contain exactly 10 letters or numbers"
            )
        if (
            self.agentcore_endpoint_name is not None
            and re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_]{0,47}", self.agentcore_endpoint_name
            )
            is None
        ):
            raise ConfigurationError(
                "AGENTCORE_ENDPOINT_NAME must start with a letter and contain at "
                "most 48 letters, numbers, or underscores"
            )
        if (
            self.claim_agentcore_endpoint_name is not None
            and re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_]{0,47}",
                self.claim_agentcore_endpoint_name,
            )
            is None
        ):
            raise ConfigurationError(
                "CLAIM_AGENTCORE_ENDPOINT_NAME must start with a letter and "
                "contain at most 48 letters, numbers, or underscores"
            )
