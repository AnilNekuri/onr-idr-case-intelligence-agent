"""AgentCore adapter for the conversational claim-intake runtime."""

from collections.abc import Callable, Mapping

from app.config import ApplicationSettings
from app.models import ClaimIntakeRequest
from app.services import (
    ConversationalClaimAgent,
    create_conversational_claim_agent,
)

ClaimAgentFactory = Callable[[ApplicationSettings], ConversationalClaimAgent]


def invoke_claim_intake_agentcore(
    payload: Mapping[str, object],
    *,
    runtime_session_id: str,
    agent_factory: ClaimAgentFactory = create_conversational_claim_agent,
    settings_factory: Callable[[], ApplicationSettings] | None = None,
) -> dict[str, object]:
    """Validate one event and invoke the conversational claim agent."""
    if len(runtime_session_id.strip()) < 33:
        raise ValueError("runtime_session_id must contain at least 33 characters")
    if settings_factory is None:
        settings_factory = ApplicationSettings.from_environment
    request = ClaimIntakeRequest.model_validate(payload)
    response = agent_factory(settings_factory()).handle(
        runtime_session_id.strip(),
        request,
    )
    return response.model_dump(mode="json")
