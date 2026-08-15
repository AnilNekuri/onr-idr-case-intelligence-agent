"""Reusable deterministic test data for tool unit tests."""

from datetime import date

from app.models import Case, CaseEvent, CaseStatus, CaseType


class StubCaseRepository:
    """Minimal in-memory repository used to isolate tool behavior."""

    def __init__(self, *cases: Case) -> None:
        self._cases = {case.case_id: case for case in cases}

    def get(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def save(self, case: Case) -> None:
        self._cases[case.case_id] = case


def make_case(
    *,
    case_id: str = "CASE-1001",
    status: CaseStatus = CaseStatus.NEW,
    deadline: date = date(2026, 8, 31),
    provider_response_received: bool = False,
    missing_documents: list[str] | None = None,
    events: list[CaseEvent] | None = None,
) -> Case:
    """Create a valid synthetic case with customizable tool inputs."""
    return Case(
        case_id=case_id,
        case_type=CaseType.ONR,
        status=status,
        created_date=date(2026, 8, 1),
        open_negotiation_start_date=date(2026, 8, 2),
        open_negotiation_end_date=deadline,
        provider_name="Synthetic Provider A",
        provider_response_received=provider_response_received,
        missing_documents=missing_documents or [],
        events=events or [],
    )
