"""Expected boundary examples for deterministic deadline risk."""

from datetime import date, timedelta

import pytest

from app.tools.case_tool import CaseNotFoundError
from app.tools.deadline_risk_tool import (
    DeadlineRisk,
    calculate_deadline_risk,
)
from tests.unit.tool_support import StubCaseRepository, make_case


@pytest.mark.parametrize(
    ("days_remaining", "expected_risk"),
    [
        (-1, DeadlineRisk.MISSED),
        (0, DeadlineRisk.HIGH),
        (3, DeadlineRisk.HIGH),
        (4, DeadlineRisk.MEDIUM),
        (7, DeadlineRisk.MEDIUM),
        (8, DeadlineRisk.LOW),
    ],
)
def test_deadline_risk_boundaries(
    days_remaining: int,
    expected_risk: DeadlineRisk,
) -> None:
    current_date = date(2026, 8, 10)
    deadline = current_date + timedelta(days=days_remaining)
    case = make_case(deadline=deadline)

    result = calculate_deadline_risk(
        StubCaseRepository(case),
        case.case_id,
        current_date=current_date,
    )

    assert result.deadline == deadline
    assert result.days_remaining == days_remaining
    assert result.risk is expected_risk


def test_deadline_risk_rejects_unknown_case() -> None:
    with pytest.raises(CaseNotFoundError, match="CASE-9999"):
        calculate_deadline_risk(
            StubCaseRepository(),
            "CASE-9999",
            current_date=date(2026, 8, 10),
        )
