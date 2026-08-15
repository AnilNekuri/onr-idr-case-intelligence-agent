"""Deterministic chronological case timeline construction."""

from app.models import CaseEvent
from app.repositories import CaseRepository
from app.tools.case_tool import require_case


def get_case_timeline(
    repository: CaseRepository,
    case_id: str,
) -> list[CaseEvent]:
    """Return case events chronologically without mutating stored facts."""
    case = require_case(repository, case_id)
    return sorted(case.events, key=lambda event: event.date)
