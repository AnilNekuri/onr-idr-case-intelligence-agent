"""Client for the dedicated conversational claim-intake AgentCore runtime."""

import json
from typing import Any

import boto3  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.config import ApplicationSettings, ConfigurationError
from app.models import ClaimIntakeRequest, ClaimIntakeResponse


class ClaimIntakeInvocationError(RuntimeError):
    """Raised when the claim-intake runtime response is invalid."""


class ClaimIntakeAgentCoreClient:
    """Invoke the stable conversational claim-intake endpoint."""

    def __init__(
        self,
        runtime_arn: str,
        endpoint_name: str,
        runtime_client: Any,
    ) -> None:
        self._runtime_arn = runtime_arn
        self._endpoint_name = endpoint_name
        self._runtime_client = runtime_client

    def invoke(
        self,
        request: ClaimIntakeRequest,
        *,
        runtime_session_id: str,
    ) -> ClaimIntakeResponse:
        """Send one structured intake event and validate the response."""
        response = self._runtime_client.invoke_agent_runtime(
            agentRuntimeArn=self._runtime_arn,
            qualifier=self._endpoint_name,
            runtimeSessionId=runtime_session_id,
            payload=request.model_dump_json(exclude_none=True).encode("utf-8"),
        )
        result = self._decode_response(response)
        try:
            return ClaimIntakeResponse.model_validate(result)
        except ValidationError as error:
            raise ClaimIntakeInvocationError(
                "Claim-intake AgentCore returned an invalid response"
            ) from error

    @staticmethod
    def _decode_response(response: Any) -> dict[str, object]:
        body = response.get("response")
        if body is None:
            raise ClaimIntakeInvocationError(
                "Claim-intake AgentCore response had no body"
            )
        try:
            if hasattr(body, "read"):
                raw = body.read()
            elif isinstance(body, (bytes, bytearray, str)):
                raw = body
            else:
                raw = b"".join(body)
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            result = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ClaimIntakeInvocationError(
                "Claim-intake AgentCore returned invalid JSON"
            ) from error
        if not isinstance(result, dict):
            raise ClaimIntakeInvocationError(
                "Claim-intake AgentCore response was not an object"
            )
        return result


def create_claim_intake_agentcore_client(
    settings: ApplicationSettings,
) -> ClaimIntakeAgentCoreClient:
    """Construct the configured conversational claim-intake client."""
    if settings.claim_agentcore_runtime_arn is None:
        raise ConfigurationError(
            "CLAIM_AGENTCORE_RUNTIME_ARN is required for remote claim intake"
        )
    if settings.claim_agentcore_endpoint_name is None:
        raise ConfigurationError(
            "CLAIM_AGENTCORE_ENDPOINT_NAME is required for remote claim intake"
        )
    session = boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )
    return ClaimIntakeAgentCoreClient(
        settings.claim_agentcore_runtime_arn,
        settings.claim_agentcore_endpoint_name,
        session.client("bedrock-agentcore"),
    )
