"""Thin AgentCore request adapter for the existing grounded case agent."""

from collections.abc import Callable, Mapping
from datetime import date

from app.config import ApplicationSettings
from app.services import GroundedCaseAgent, create_grounded_case_agent

AgentFactory = Callable[[ApplicationSettings], GroundedCaseAgent]


def invoke_agentcore(
    payload: Mapping[str, object],
    *,
    agent_factory: AgentFactory = create_grounded_case_agent,
    settings_factory: Callable[[], ApplicationSettings]
    | None = None,
) -> dict[str, object]:
    """Validate one AgentCore payload and call the unchanged agent use case."""
    case_id = _required_text(payload, "case_id")
    question = _question(payload)
    current_date = _current_date(payload)

    if settings_factory is None:
        settings_factory = ApplicationSettings.from_environment
    agent = agent_factory(settings_factory())
    return agent.answer(
        case_id=case_id,
        question=question,
        current_date=current_date,
    ).model_dump()


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _question(payload: Mapping[str, object]) -> str:
    value = payload.get("question", payload.get("prompt"))
    if not isinstance(value, str) or not value.strip():
        raise ValueError("question or prompt must be a non-empty string")
    return value.strip()


def _current_date(payload: Mapping[str, object]) -> date:
    value = payload.get("current_date")
    if value is None:
        return date.today()
    if not isinstance(value, str):
        raise ValueError("current_date must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("current_date must use YYYY-MM-DD") from error
